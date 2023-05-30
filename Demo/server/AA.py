import socket
import threading
import json
from db_operations import DBOperations
import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64
import logging

f = "%(asctime)s------>%(message)s"
logging.basicConfig(level=logging.INFO, format=f)


class AA:
    def __init__(self, aa_id, host, port):
        self.info_aa2as = None  # 对所有AS广播的信息
        self.aa_id = aa_id  # 当前AA的id
        self.host = host  # 监听ip
        self.port = port  # 监听端口
        self.db_operations = DBOperations("113.54.244.107", 3306, "q", "123")

    def start_server(self):
        """
        开启监听
        :return:
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"AA {self.aa_id} server is listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"AA {self.aa_id} Received connection from", client_address)
            client_thread = threading.Thread(target=self.verify_user, args=(client_socket,))
            client_thread.start()

    def verify_user(self, client_socket):
        """
        对subject发送的信息进行验证,验证通过则签名
        :param client_socket:
        :return:
        """
        # 接收到的用户信息
        user_data = client_socket.recv(1024).decode("utf-8")
        if not user_data:
            print("not user data!")
            client_socket.close()
            return
        user_data = json.loads(user_data)
        logging.info(f"AA{self.aa_id}:接收到用户的信息--->>>{user_data['user_info']['username']}")
        # 对用户信息进行hash
        user_info_hash = SHA256.new(str(user_data['user_info']).encode()).hexdigest()
        # 对用户信息进行检验
        authenticated = self.db_operations.authenticate_user(user_info_hash)
        # 返回信息
        if authenticated:
            # 签名信息
            logging.info(f"AA{self.aa_id}:用户信息校验成功--->>>{user_data['user_info']['username']}")
            sign_info = self.sign_user_info(user_data['user_info'])
            # 对user发送的信息
            info_aa2user = {
                "event_type": "send_signature",
                'status': "authenticated",
                'sign_info': sign_info,
                "timestamp": datetime.datetime.now().isoformat()
            }
            # 将信息发送到AS
            self.info_aa2as = {
                "event_type": "send_vote_info",
                "user_info": user_data["user_info"],
                "request_info": user_data["request_info"],
                "timestamp": datetime.datetime.now().isoformat()
            }
            # 向所有AS进行广播
            self.send_info_aa2as()
        # 若验证不通过
        else:
            info_aa2user = {
                "event_type": "send_signature",
                "status": "unauthenticated",
                "timestamp": datetime.datetime.now().isoformat()
            }

        logging.info(f"AA{self.aa_id}:向用户返回签名后的信息")
        client_socket.send(json.dumps(info_aa2user).encode("utf-8"))
        client_socket.close()

    def send_info_aa2as(self):
        """
        将检验并签名后的信息广播给as
        :return:
        """
        as_addrs = []
        with open("AS_addrs", "r") as f:
            for addr in f.readlines():
                addr = addr.split(":")
                as_ip = addr[0]
                as_port = addr[1]
                as_addrs.append((as_ip, as_port))

        for index, as_addr in enumerate(as_addrs):
            socket_as = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_as.connect((as_addr[0], int(as_addr[1])))
            logging.info(f"AA{self.aa_id}:向AS{index + 1}节点发送签名信息......")
            while True:
                socket_as.sendall(json.dumps(self.info_aa2as).encode("utf-8"))
                data = socket_as.recv(1024)
                if not data:
                    socket_as.close()
                    break

    def sign_user_info(self, user_info):
        # 使用私钥对用户信息进行签名
        private_key = self.read_private_key()
        message = str(user_info).encode()  # 待签名信息
        h = SHA256.new(message)  # 待签名信息的摘要
        signature = pkcs1_15.new(private_key).sign(h)
        encoded_signature = base64.b64encode(signature).decode('utf-8')

        return encoded_signature

    def read_private_key(self):
        # 从文件中读取私钥
        with open(f"private_key_{self.aa_id}.key", 'rb') as f:
            return RSA.import_key(f.read())


def run(aa_id):
    aa = AA(aa_id, "0.0.0.0", 2000 + aa_id)
    aa.start_server()


if __name__ == "__main__":
    for i in range(1, 6):
        t = threading.Thread(target=run, args=(i,))
        t.start()
