import json

import mysql.connector
from Crypto.Hash import SHA256
import datetime

TOKEN_TTL = 60  # token存活时间


class DBOperations:
    def __init__(self, db_host, db_port, db_user, db_password, db_name="iot_devices"):
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.connection = self.connect_to_db()

    def connect_to_db(self):
        """
        连接数据库
        :return:
        """
        connection = mysql.connector.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name
        )
        return connection

    def authenticate_user(self, user_hash):
        """
        查询用户的信息是否正确
        :param user_hash:
        :return:
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM users WHERE user_hash='{user_hash}'")
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    def verify_token(self, tokens):
        """
        验证token,同时获取允许的操作列表
        :return:
        """
        cursor = self.connection.cursor()

        cursor.execute(f"SELECT * FROM gk_tokens WHERE tokens='{tokens}'")
        result = cursor.fetchone()
        cursor.close()
        status = {
            "status": result is not None,
            "access_list": result[4] if result is not None else None
        }
        return status

    def register_token(self, token_data, user_info):
        """
        向数据库中添加token信息
        :param token_data:
        :param user_info:
        :return:
        """
        user_hash = SHA256.new(json.dumps(user_info["user_info"]).encode()).hexdigest()
        request_device = user_info["request_info"]["device_ip"]
        tokens = token_data["token"]
        access_list = str(token_data["access_list"])
        signature = user_info["sign_info"]
        t_timestamp = datetime.datetime.now().isoformat()
        cursor = self.connection.cursor()
        # cursor.execute(f"INSERT INTO gk_tokens (user_hash, request_device,tokens,access_list,signature,t_timestamp) VALUES ('{str(user_hash)}', '{str(request_device)}','{str(tokens)}','{str(access_list)}','{str(signature)}','{str(t_timestamp)}')")
        query = f"INSERT INTO gk_tokens (user_hash, request_device,tokens,access_list,signature,t_timestamp) VALUES (%s,%s,%s,%s,%s,%s)"
        values = (user_hash, request_device, tokens, access_list, signature, t_timestamp)
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def is_token_registered(self, user_info):
        """
        检查用户是否用相对应的token
        :return:
        """
        cursor = self.connection.cursor()
        user_hash = SHA256.new(json.dumps(user_info["user_info"]).encode()).hexdigest()
        request_device = user_info["request_info"]["device_ip"]
        signature = user_info["sign_info"]
        t_timestamp_new = datetime.datetime.now()
        cursor.execute(f"SELECT * FROM gk_tokens WHERE user_hash='{user_hash}' AND request_device='{request_device}' AND signature='{signature}'")
        result = cursor.fetchone()
        cursor.close()
        # t_timestamp_old = result[-1] if result is not None else None
        # time_difference = int(t_timestamp_new.timestamp() - t_timestamp_old.timestamp())
        user_status = {
            "status": result is not None,
            "token": result[3] if result is not None else None
        }
        return user_status


if __name__ == '__main__':
    user_info = {
        "event_type": "get_vote_rst",
        "user_info": {
            'username': 'd4wn',
            'password': 'root'
        },
        "sign_info": 'tShW/BhsCJ00VD9sTECuAEl0H2qhKgyB+cK0coUmcSD+EhSxkI9PBHqGzKsmEYe2ZYAV07lRU4bsaw+hhrxBJYr2wX/CsKO+NK7prGXxqnjwBOAH5Wkw98R/LNXaN69lgjz9mb6eBq/7ZkidKrjWpx9jwGEO/2LAPIXTUu/FcvaE4USthjXkXDSdqE5UwykbwfYsuiir0UuJyMY2/UX36giJnvCfnWRutYvuSVORiWbwohEZ+LBIj0pOxxsHfmW0SOh5O9RdK9XZZGJ2r3U3xf9DYwww+9X22Vu5hAtHWSl9AJtAC8iZ2yoxmqRiqmvA+3tkgu6jzzd8aHFKKXQnLg==',
        "request_info": {
            "device_ip": '192.168.1.2',
            "access_list": ["admin_operation",  # 管理员操作,
                            "normal_operation",  # 对设备进行一些常规操作的权限，如测量血压、心率等数据
                            "guest_access"  # 访客权限，只能查看设备的状态或者一些常规的信息
                            ]
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
    d = DBOperations("113.54.228.185", 3306, "q", "123")
    tmp = d.is_token_registered(user_info)
    # print(type(tmp))
