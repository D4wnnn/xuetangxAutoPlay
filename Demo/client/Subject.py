import socket
import json
import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64
import logging

f = "%(asctime)s------>%(message)s"
logging.basicConfig(level=logging.INFO, format=f)


class Subject:
    def __init__(self, AA_ip, AA_port, GK_ip, GK_port, username, password, device_ip, access_list):
        self.token = None
        self.client_socket = None
        self.AA_ip = AA_ip  # AA地址
        self.AA_port = AA_port  # AA端口
        self.GK_ip = GK_ip  # GK地址
        self.GK_port = GK_port  # GK地址
        self.username = username  # 用户名
        self.password = password  # 密码
        self.device_ip = device_ip  # 设备ip
        self.access_list = access_list  # 访问权限列表
        self.signature = None

    def get_signature(self):
        """
        将用户信息发送到AA
        :return: 认证结果和签名信息
        """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.AA_ip, self.AA_port))
        auth_data = {
            "event_type": "get_signature",
            "user_info": {
                'username': self.username,
                'password': self.password
            },
            "request_info": {
                "device_ip": self.device_ip,
                "access_list": self.access_list
                # "access_list": ["admin_operation",  # 管理员操作,
                #                 "normal_operation",  # 对设备进行一些常规操作的权限，如测量血压、心率等数据
                #                 "guest_access"  # 访客权限，只能查看设备的状态或者一些常规的信息
                #                 ]
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
        # 向AA发送验证信息
        logging.info("Subject:向AA发送用户请求信息")
        self.client_socket.send(json.dumps(auth_data).encode("utf-8"))
        # 接收AA签名后的信息
        response = None
        while True:
            # 从AA接收到的信息
            recv_aa = self.client_socket.recv(1024).decode("utf-8")
            if not recv_aa:
                self.client_socket.close()
                break
            response = json.loads(recv_aa)
        self.signature = response['sign_info'] if response['status'] == 'authenticated' else None
        if response["status"] == "authenticated":
            logging.info("Subject:成功从AA获取签名")
        else:
            logging.error("Subject:AA拒绝签名！")
            exit(-1)

    def get_token(self):
        """
        检验是否签名，若签名成功，则将签名后的信息发送给GK,获得token
        :return:
        """
        # if self.signature is None:
        #     logging.error("Subject:身份认证失败")
        #     exit(0)
        # logging.info("Subject:身份认证成功")
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.GK_ip, self.GK_port))
        # 向GK发送的信息
        send_info = {
            "event_type": "get_token",
            "user_info": {
                'username': self.username,
                'password': self.password
            },
            "sign_info": self.signature,
            # "sign_info": base64.b64encode("hello".encode("utf-8")).decode("utf-8"),
            "request_info": {
                "device_ip": self.device_ip,
                "access_list": self.access_list
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
        # 向GK发送信息
        logging.info("Subject:向GK发送签名后的信息")
        self.client_socket.send(json.dumps(send_info).encode("utf-8"))
        response = None
        while True:
            recv_data = self.client_socket.recv(1024).decode("utf-8")
            if not recv_data:
                self.client_socket.close()
                break
            response = json.loads(recv_data)
        if response["msg"] == "auth_failure":
            logging.error("Subject:GK拒绝发放token！")
            exit(-1)
        else:
            self.token = response["token"]
            logging.info("Subject:成功获取token: " + response["token"])

    def get_userinfo(self):
        """
        获取字典格式的用户信息
        :return:
        """
        return {
            'username': self.username,
            'password': self.password
        }

    def connect_device(self):
        """
        用户拿着token去请求设备,成功连接后就操作设备
        :return:
        """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.GK_ip, self.GK_port))
        # 向GK请求连接设备
        auth_data = {
            "event_type": "get_access",
            "token": self.token,
            "device_ip": self.device_ip,
            "event_timestamp": datetime.datetime.now().isoformat(),
        }
        self.client_socket.send(json.dumps(auth_data).encode("utf-8"))
        # 接收GK返回的信息
        response = self.client_socket.recv(1024).decode("utf-8")
        response = json.loads(response)
        if response["auth"]:
            logging.info("Subject:GK验证通过该token")
            while True:
                command = input("Enter device command(or type 'CLOSE' to close the connection): ")
                if command == "CLOSE":
                    self.client_socket.close()
                    break
                command_info = {
                    "event_type": "exec_command",
                    "command": command,
                    "event_timestamp": datetime.datetime.now().isoformat(),
                }
                self.client_socket.sendall(json.dumps(command_info).encode("utf-8"))
                # 接收GK返回的命令执行结果
                recv_data = self.client_socket.recv(1024)
                if not recv_data:
                    logging.error(f"Subject:GK断开连接")
                    self.client_socket.close()
                    break
                resp = json.loads(recv_data.decode("utf-8"))
                if resp["msg"] == "failure":
                    # logging.error("Subject:GK执行命令失败!")
                    print("Subject:GK执行命令失败!")
                    # self.client_socket.close()
                    # break
        else:
            logging.error(f"Subject:GK拒绝该token")
            self.client_socket.close()

    def close_connection(self):
        self.client_socket.close()


if __name__ == "__main__":
    access_list = ["increase_brightness",  # 增加灯光亮度
                   "increase_brightness",  # 降低灯光亮度
                   "light_off"  # 关灯
                   ]
    subject = Subject("192.168.126.140", 2001, "192.168.126.140", 3001, "d4wn", "root", "192.168.1.2", access_list)
    subject.get_signature()  # 向AA发送信息,获取签名
    subject.get_token()  # 向GK发送签名后的信息
    subject.connect_device()  # 连接设备
