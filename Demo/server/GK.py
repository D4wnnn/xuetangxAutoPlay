import base64
import socket
import threading
import json

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from user_behavior_monitor import UserBehaviorMonitor
from db_operations import DBOperations
import datetime
import logging

f = "%(asctime)s------>%(message)s"
logging.basicConfig(level=logging.INFO, format=f)


class GK:
    def __init__(self, gk_id, AS_ip, AS_port, host, port):
        self.gk_id = gk_id  # 当前GK的id
        self.AS_ip = AS_ip  # GK即将访问的AS的ip
        self.AS_port = AS_port  # GK即将访问的AS的端口
        self.host = host  # 当前GK监听的地址
        self.port = port  # 当前GK监听的端口
        self.db_operations = DBOperations("113.54.244.107", 3306, "q", "123")
        self.user_behavior_monitor = UserBehaviorMonitor()

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"GK {self.gk_id} server is listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"GK {self.gk_id} Received connection from", client_address)
            client_thread = threading.Thread(target=self.handle, args=(client_socket,))
            client_thread.start()

    def handle(self, client_socket):
        """
        处理user发送的信息
        :param client_socket:
        :return:
        """
        # 接收的信息
        received_data = client_socket.recv(1024).decode("utf-8")
        if not received_data:
            print("no data!")
            client_socket.close()
            return
        received_data = json.loads(received_data)
        # 若是user发送来的消息:转发给AS
        if received_data["event_type"] == "get_token":
            user_info = {
                "event_type": "get_vote_rst",
                "user_info": received_data["user_info"],
                "sign_info": received_data["sign_info"],
                "request_info": received_data["request_info"],
                "timestamp": datetime.datetime.now().isoformat()
            }
            logging.info(f"GK{self.gk_id}:接收到了user发送的身份签名")
            user_status = self.db_operations.is_token_registered(user_info)
            if not user_status["status"]:  # 若缓冲区没有相应的信息,就去请求AS
                logging.info(f"GK{self.gk_id}:未在缓冲区中找到相应信息")
                # 首先对签名进行校验
                if not self.verify_signature(received_data["sign_info"], received_data["user_info"]):
                    # 若数字签名检验未通过
                    logging.info(f"GK{self.gk_id}:数字校验信息未通过")
                    token = None
                    msg = "auth_failure"
                    pass
                else:
                    logging.info(f"GK{self.gk_id}:数字校验通过")
                    msg = "success"

                    # 连接AS
                    client_socket_gk_as = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket_gk_as.connect((self.AS_ip, self.AS_port))
                    # 向AS发送信息并获取token
                    user_info = {
                        "event_type": "get_vote_rst",
                        "user_info": received_data["user_info"],
                        "sign_info": received_data["sign_info"],
                        "request_info": received_data["request_info"],
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    client_socket_gk_as.send(json.dumps(user_info).encode("utf-8"))
                    token_data = None
                    while True:
                        recv_data = client_socket_gk_as.recv(1024).decode("utf-8")
                        if not recv_data:
                            client_socket_gk_as.close()
                            break
                        token_data = json.loads(recv_data)
                    logging.info(f"GK{self.gk_id}:接收到了AS发送的token")
                    # 在数据库中存取token和权限列表
                    logging.info(f"GK{self.gk_id}:向数据库中存取token及访问列表")
                    token = token_data["token"]
                    self.db_operations.register_token(token_data, user_info)
            else:  # 若缓冲区有相应的信息,就取出来
                msg = "success"
                logging.info(f"GK{self.gk_id}:在缓冲区中找到了相应信息")
                token = user_status['token']
            send_info = {
                "event_type": "send_token",
                "msg": msg,
                "token": token,
                "timestamp": datetime.datetime.now().isoformat()
            }
            client_socket.sendall(json.dumps(send_info).encode("utf-8"))
            client_socket.close()
        elif received_data["event_type"] == "get_access":
            # 验证token
            tokens = received_data['token']
            token_status = self.db_operations.verify_token(tokens)
            access_list = None
            if token_status['status']:
                authenticated = True
                access_list = token_status['access_list']
            else:
                authenticated = False
            # 若token验证成功
            if authenticated:
                response = {
                    "event_type": "send_access_rst",
                    "auth": True,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                # 启动UserBehaviorMonitor的监控线程，用于检查特定设备（即device_data["hostname"]）的行为是否异常
                self.user_behavior_monitor.start_monitoring(received_data["device_ip"])  # 设备ip
                # 如果需要,可以设定检查间隔
                self.user_behavior_monitor.set_check_interval(received_data["device_ip"], 2)
                # 创建一个新的线程，用于监听来自客户端设备的事件并将其添加到UserBehaviorMonitor的事件日志中
                event_listener_thread = threading.Thread(target=self.event_listener, args=(client_socket, received_data["device_ip"], access_list))
                event_listener_thread.start()
                client_socket.sendall(json.dumps(response).encode("utf-8"))
            else:  # 若token无效
                response = {
                    "event_type": "send_access_rst",
                    "auth": False,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                client_socket.sendall(json.dumps(response).encode("utf-8"))
                client_socket.close()

    def event_listener(self, client_socket, device_ip, access_list):
        """
        监听user的操作,写进日志，但是并不分析异常行为
        :param access_list:
        :param client_socket:
        :param device_ip:
        :return:
        """
        while True:
            # 接收用户发送的命令
            event_data = client_socket.recv(1024).decode("utf-8")
            if not event_data:
                client_socket.close()
                break
            # 若当前设备的监控线程为None，则代表检测到异常，断开连接
            if self.user_behavior_monitor.monitor_threads[device_ip] is None:
                client_socket.close()
                break
            event_data = json.loads(event_data)
            logging.info(f"GK:记录事件:{device_ip}--{event_data['event_timestamp']}--{event_data['command']}")
            # 允许的行为
            if event_data['command'] in access_list:
                msg = "success"
            else:
                msg = "failure"
            # 向日志中记录操作
            self.user_behavior_monitor.log_event(device_ip, event_data["event_timestamp"], event_data["command"])
            # 发送命令执行结果给用户
            command_result = {
                "event_type": "send_command_rst",
                "msg": msg,
                "timestamp": datetime.datetime.now().isoformat()
            }
            client_socket.sendall(json.dumps(command_result).encode("utf-8"))
        client_socket.close()

    def verify_signature(self, signature_b64, user_info):
        """
        对签名进行校验
        :return:
        """
        with open('public_key_1.key', 'rb') as f:
            public_key = RSA.import_key(f.read())
        # 验证数字签名
        signature = base64.b64decode(signature_b64)
        h = SHA256.new(str(user_info).encode())

        try:
            pkcs1_15.new(public_key).verify(h, signature)
            return True

        except (ValueError, TypeError):
            return False


def run(gk_id):
    gk = GK(gk_id, "192.168.126.140", 1001, "0.0.0.0", 3000 + gk_id)
    gk.start_server()


if __name__ == "__main__":
    for i in range(1, 31):
        t = threading.Thread(target=run, args=(i,))
        t.start()
