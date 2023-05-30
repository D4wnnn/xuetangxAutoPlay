import logging
import threading
import time
from datetime import datetime
from collections import defaultdict


class UserBehaviorMonitor:
    def __init__(self, default_check_interval=3, threshold=2):
        self.default_check_interval = default_check_interval
        self.threshold = threshold
        self.event_log = defaultdict(list)
        self.check_intervals = defaultdict(lambda: self.default_check_interval)
        self.monitor_threads = {}

    def set_check_interval(self, device_id, check_interval):
        self.check_intervals[device_id] = check_interval

    def log_event(self, device_id, timestamp, event_type):
        self.event_log[device_id].append((timestamp, event_type))

    def start_monitoring(self, device_id):
        monitor_thread = threading.Thread(target=self.monitor_behavior, args=(device_id,))
        self.monitor_threads[device_id] = monitor_thread
        monitor_thread.start()

    def monitor_behavior(self, device_id):
        while True:
            time.sleep(self.check_intervals[device_id])
            events = self.event_log[device_id]
            if self.detect_abnormal_behavior(events):
                logging.warning(f"monitor:设备{device_id}异常行为超过阈值!")
                # TODO:对设备进行质询
                # 假设质询不通过:停止监控，并设置监控线程为None，此后监听事件会检测到None，然后结束对话
                self.monitor_threads[device_id] = None
                break

    def detect_abnormal_behavior(self, events):
        """
        检测不正常行为
        :param events:
        :return:
        """
        format_string = "%Y-%m-%dT%H:%M:%S.%f"
        late_night_events = []
        for event in events:
            dt = datetime.strptime(event[0], format_string)
            if 0 <= dt.hour <= 1:
                late_night_events.append(event)
        # 计算凌晨事件的数量，并将结果存储在late_night_event_count变量中。
        late_night_event_count = len(late_night_events)
        # 计算凌晨事件的频率
        late_night_event_frequency = late_night_event_count / 4  # Hours between 1 and 5
        logging.info(f"monitor:异常行为频率:{late_night_event_frequency}/阈值{self.threshold}")
        # 如果凌晨事件频率大于预设阈值（self.threshold），则返回True，表示检测到异常行为。否则，返回False，表示没有检测到异常行为。
        return late_night_event_frequency > self.threshold
