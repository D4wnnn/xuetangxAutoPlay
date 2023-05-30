import socket
import threading
import json

from Crypto.Hash import SHA256

from db_operations import DBOperations
import datetime
import uuid
import logging

format = "%(asctime)s------>%(message)s"
logging.basicConfig(level=logging.INFO, format=format)


class AS:
    def __init__(self, as_id, host, port):
        self.as_id = as_id  # 当前AS节点id
        self.host = host  # 当前AS节点监听的地址
        self.port = port  # 当前AS节点监听的端口
        self.db_operations = DBOperations("113.54.244.107", 3306, "q", "123")
        self.vote_buffer = {}  # 当前AS节点投票缓冲区
        # {'user_hash':{'ip':[]}}

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"AS {self.as_id} server is listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"AS {self.as_id} Received connection from", client_address)
            client_thread = threading.Thread(target=self.handle, args=(client_socket,))
            client_thread.start()

    def handle(self, client_socket):
        """
        处理AA或者GK发送来的信息
        :param client_socket:
        :return:
        """
        received_data = client_socket.recv(1024).decode("utf-8")
        if not received_data:
            print("no data!")
            client_socket.close()
            return
        received_data = json.loads(received_data)
        # 若是AA发送来的消息
        if received_data["event_type"] == "send_vote_info":
            # TODO 处理AA发送来的信息
            logging.info(f"AS{self.as_id}:接收到了AA发送的用户信息")
            # 判断投票缓冲区是否有该信息
            user_hash = SHA256.new(str(received_data['user_info']).encode("utf-8")).hexdigest()
            device_ip = received_data['request_info']['device_ip']
            access_list = received_data['request_info']['access_list']
            # 若第一次投票该用户则创建列表
            if user_hash not in self.vote_buffer.keys():
                self.vote_buffer[user_hash] = {}
            # 向投票缓冲区存放信息{'user_hash':{'ip':[]}}
            self.vote_buffer[user_hash][device_ip] = access_list
            client_socket.close()
        # 若是GK发送来的消息
        elif received_data["event_type"] == "get_vote_rst":
            logging.info(f"AS{self.as_id}:接收到了GK发送的签名信息")
            # TODO:判断投票结果
            # 用户信息hash
            user_hash = SHA256.new(str(received_data['user_info']).encode("utf-8")).hexdigest()
            # 在投票缓冲区中查找，查找到后删除
            device_ip = received_data['request_info']['device_ip']
            access_list = self.vote_buffer[user_hash][device_ip]
            self.vote_buffer[user_hash].pop(device_ip)
            # 生成token
            token = str(uuid.uuid4())
            # 发送给GK的信息
            send_info = {
                "event_type": "send_vote_rst",
                "token": token,
                "access_list": access_list,
                "timestamp": datetime.datetime.now().isoformat()
            }
            client_socket.sendall(json.dumps(send_info).encode("utf-8"))
            client_socket.close()


def run(as_id):
    as_ = AS(as_id, "0.0.0.0", 1000 + as_id)
    as_.start_server()


if __name__ == "__main__":
    for i in range(1, 5):
        t = threading.Thread(target=run, args=(i,))
        t.start()
