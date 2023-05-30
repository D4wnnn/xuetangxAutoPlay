# -*- coding: utf-8 -*
from generator import Generator
from Crypto.Hash import SHA256
import time


class Accumulator:
    pool_number = 32      # 32个池
    min_pool_size = 64    # 池的最小长度

    reseed_interval = 0.1

    P = []

    def __init__(self):
        self.P = [b''] * self.pool_number
        self.ReseedCnt = 0              # 重新产生种子的计数器
        self.generator = Generator()    # 初始化生成器
        self.last_seed = time.time()

    # 生成伪随机数，n为生成的伪随机数的字节数
    def random_data(self, n):
        # 若超过一定时间或者第一个池子没填满就进行填充
        if len(self.P[0]) >= self.min_pool_size or time.time() - self.last_seed > self.reseed_interval:
            # 填充记录+1
            self.ReseedCnt += 1
            s = b''
            for i in range(self.pool_number):
                if self.ReseedCnt % (2 ** i) == 0:
                    s += SHA256.new(SHA256.new(self.P[i]).digest()).digest()
                    # self.P[i] = b''
                    # 改6
                    self.P[i] = s  # 更新池子
            self.generator.reseed(s)  # 更新key(根据原先的key和当前池子取哈希)
            self.last_seed = time.time()  # 更新上一次播种时间

        return self.generator.pseudo_random_data(n)  # 返回伪随机字节串

    def add_random_event(self, s, i, e):
        # s source number
        # i pool number
        # e subject data
        assert 0 < len(e) <= 32 and 0 <= s <= 255 and 0 <= i <= 31
        self.P[i] = self.P[i] + (str(s) + str(len(e))).encode() + e
