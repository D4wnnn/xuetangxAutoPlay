# -*- coding: utf-8 -*


from Crypto.Cipher import AES
from Crypto.Hash import SHA256


class CustomCounter:
    def __init__(self, nbits, initial_value=0, little_endian=True):
        self.nbits = nbits
        self.bit_count = nbits // 8
        self.value = initial_value
        self.little_endian = little_endian

    def increment(self):
        self.value += 1
        if self.value >= 2 ** self.nbits:
            self.value = 0

    def get_value(self):
        if self.little_endian:
            return self.value.to_bytes(self.bit_count, byteorder='little')
        else:
            return self.value.to_bytes(self.bit_count, byteorder='big')

    def __str__(self):
        return str(self.value)

    def get_config(self):
        return {
            'counter_len': self.bit_count,
            'prefix': b'',
            'suffix': b'',
            'initial_value': self.value,
            'little_endian': self.little_endian
        }

# 生成伪随机数据


class Generator:
    block_size = AES.block_size  # 分组数目16字节
    key_size = 32  # 密钥长度

    def __init__(self):
        # self.counter = Counter.new(
        #     nbits=self.block_size * 8, initial_value=0, little_endian=True)  # 计数器，每次call此计数器其值加一
        # # nbits参数表示计数器的位数，即计数器能表示的最大整数值。在此示例中，它是块大小的8倍
        # # little_endian参数表示计数器以小端字节序进行存储。
        # 改1：
        self.counter = CustomCounter(
            nbits=self.block_size * 8, initial_value=0, little_endian=True)
        self.key = None

    # 重新生成种子,key会根据种子更新
    def reseed(self, seed):
        if self.key is None:
            self.key = b'\0' * self.key_size

        self.set_key(SHA256.new(SHA256.new(self.key + seed).digest()).digest())
        # self.counter()
        # 改：
        self.counter.increment()

    # 设定新的密钥
    def set_key(self, key):
        self.key = key
        self.cipher = AES.new(
            key, AES.MODE_CTR, counter=self.counter.get_config())

    # √分组 生成AES加密数据块，对计数器字节值加密，n为分组数目
    def generate_blocks(self, n):

        assert self.key != b''
        result = b''
        for i in range(n):
            # result += self.cipher.encrypt(self.counter())
            # 改3
            result += self.cipher.encrypt(self.counter.get_value())  # 计数器的字节值
            self.counter.increment()  # 计数器值手动+1
        return result  # 16n字节的字符串

    # 生成随机数据，n为生成随机数据的字节数
    def pseudo_random_data(self, n):
        assert 0 <= n <= 2 ** 20  # 限定生成的字节数要合理
        # 生成前n个字节
        result = self.generate_blocks(
            n // 16 if n % 16 == 0 else (n // 16) + 1)[:n]

        self.key = self.generate_blocks(2)
        return result  # 返回n字节的随机数据


if __name__ == '__main__':
    # 第一步：读取种子，存入seed
    try:
        # 若存在seedfile即上次存储的状态，以便此次刚启动就能开始生成随机数
        f = open('seedfile', 'rb')
    except:
        # Linux内核下的设备文件
        with open('/dev/random', 'rb') as random_source:
            # 第一个参数为offset偏移，第二个参数从哪个位置开始偏移；默认0从文件开头，1从当前位置开，2从文件末尾
            random_source.seek(-64, 2)
            # 读取最后的64个字节
            seed = random_source.read(64)
            assert len(seed) == 64

    else:  # 没有发生异常的时候会执行
        try:
            seed = f.read(64)
            assert len(seed) == 64
        finally:
            f.close()
    g = Generator()
    g.reseed(seed)
