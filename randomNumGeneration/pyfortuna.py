# -*- coding: utf-8 -*

from accumulator import Accumulator
from seedcreator import SeedCreator


def read_seed():
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
    return seed


if __name__ == '__main__':
    accumulator = Accumulator()
    seed_creator = SeedCreator()
    # 第一步：读取种子，存入seed
    seed = read_seed()
    # 第二步：设置accumulator
    # 把根据旧的key和seed取哈希把generator中的key更新
    accumulator.generator.reseed(seed)
    # 第三步：更新seedfile
    seed_creator.seed_update(accumulator)

    n = 1  # 辅助值
    while n != 0:
        # n = input("\n(输入0退出)\n请输入生成的随机数的字节数(n>0): ")
        # 改4
        n = int(input("\n(输入0退出)\n请输入生成的随机数的字节数(n>0): "))
        if n == 0:
            print("已退出!\n")
            quit()
        elif n < 0:
            print("输入错误!!!\n")
            quit()
        else:
            # print("\n生成随机数：\n%r" % (accumulator.random_data(
            #     int(n))).encode('hex').decode('hex'))
            # 改5
            print("\n生成随机数：\n%r" % (accumulator.random_data(
                int(n))))
