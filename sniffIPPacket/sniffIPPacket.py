import pymysql
from scapy.sendrecv import sniff
from scapy.utils import wrpcap
from scapy.all import Ether, IP, TCP, Raw, DNS
from scapy.layers.http import HTTPRequest, HTTPResponse

# 保存的数据包名称
filename = 'demo.pcap'

index = 0


def save_packet_to_file(packet):
    """
    保存数据包到demo.pcap
    :param packet:
    :return:
    """
    wrpcap(filename, packet, append=True)


def analyze_raw(packet):
    """
    解析应用层协议
    :param packet: 网络包
    :return: 应用协议
    """
    tcp = packet[TCP]
    src_port, dst_port = tcp.sport, tcp.dport

    # 尝试获取应用层协议
    app_protocol = "Unknown"

    if packet.haslayer(DNS):
        app_protocol = "DNS"
    elif packet.haslayer(HTTPRequest) or packet.haslayer(HTTPResponse):
        app_protocol = "HTTP"
    else:
        # 通过端口号判断应用层协议
        well_known_ports = {
            20: "FTP",
            21: "FTP",
            22: "SSH",
            23: "TELNET",
            25: "SMTP",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            1723: "PPTP",
            3306: "MYSQL"
        }
        if src_port in well_known_ports:
            app_protocol = well_known_ports[src_port]
        elif dst_port in well_known_ports:
            app_protocol = well_known_ports[dst_port]
    if app_protocol == "Unknown":
        app_protocol = dst_port
    return app_protocol


def analyze_packet(packet):
    """
    分析文件包并且保存到数据库
    :param packet:
    :return:
    """
    # 若没有IP协议就return
    if not packet.haslayer(IP):
        return
    src_ip, dst_ip = packet[IP].src, packet[IP].dst
    # 若没有TCP协议就return
    if not packet.haslayer(TCP):
        return
    tcp = packet[TCP]
    src_port, dst_port = tcp.sport, tcp.dport
    # 若没有应用层负载，就return
    if not packet.haslayer(Raw):
        return
    # 获取应用层协议
    raw_protocol = analyze_raw(packet)
    # 跳过SSH数据包和MYSQL数据包
    if raw_protocol == "SSH" or raw_protocol == "MYSQL":
        return
    rawData = str(packet.time) + '-' + str(packet[Raw].load)
    storeData(connection, src_ip, dst_ip, src_port, dst_port, rawData, raw_protocol)


def process_packet(packet):
    """
    对抓到的数据包进行处理
    :param packet:
    :return:
    """
    save_packet_to_file(packet)  # 保存数据包到demo.pcap
    analyze_packet(packet)  # 分析文件包并且保存到数据库


def start_sniff():
    """
    开始监听
    :return:
    """
    # 0代表要捕获的数据包无限
    sniff(iface='ens33', count=0, prn=process_packet)


def storeData(connection, src_ip, dst_ip, sport, dport, data, raw_protocol):
    """
    将数据存储到数据库并打印日志
    :param connection: 数据库连接
    :param src_ip: 源ip
    :param dst_ip: 目的ip
    :param sport: 源端口
    :param dport: 目的端口
    :param data:
    :param raw_protocol: 应用层协议
    :return:
    """
    # 向数据库中插入数据包信息
    with connection.cursor() as cursor:
        sql = "insert into `entropy`(src_ip,dst_ip,sport,dport,data) values (%s,%s,%s,%s,%s)"
        cursor.execute(sql, (src_ip, dst_ip, sport, dport, data))
    connection.commit()
    # 向控制台打印日志
    global index
    index += 1
    src_ip_port = src_ip + ":" + str(sport)
    src_ip_port = "{:<23}".format(src_ip_port).replace(" ", "-")
    print(f"successful capture-->No.{str(index)}\t{src_ip_port}----{raw_protocol}------>{dst_ip}:{dport}")


def init_database(clear):
    """
    初始化数据库
    :param clear: 是否清空之前的数据(方便调试)
    :return: 数据库连接
    """
    conn = pymysql.connect(host='113.54.244.107',
                           port=3306,
                           user='qy',
                           password='root',
                           database='tmp',
                           charset='utf8',
                           cursorclass=pymysql.cursors.DictCursor)
    # 清空表
    if clear:
        with conn.cursor() as cursor:
            cursor.execute('drop table if exists entropy;')
    conn.commit()
    # 创建表
    with conn.cursor() as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS `entropy`(`id` INT AUTO_INCREMENT,`src_ip` CHAR(20),`dst_ip` CHAR(20),`sport` CHAR(6),`dport` CHAR(6),`data` MEDIUMTEXT,PRIMARY KEY (`id`))ENGINE=InnoDB DEFAULT CHARSET=utf8;')
    conn.commit()
    return conn


def main():
    global connection
    connection = init_database(clear=True)  # 初始化数据库并得到数据库连接对象,cleat=True代表清空之前的数据
    start_sniff()  # 开始监听


if __name__ == '__main__':
    main()
