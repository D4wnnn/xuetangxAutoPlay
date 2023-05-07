# -*- coding: utf-8 -*-
# @Time    : 2023/5/7 21:00
# @Author  : D4wn
# @FileName: main.py
# @Software: PyCharm
# @Blog    : https://blog.acdawn.cn
import time

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# chrome.exe --remote-debugging-port=9222 --user-data-dir="D:/selenium_test"
# base_url = 'https://www.xuetangx.com/learn/EST08091001150/EST08091001150/14767710/video/30164547?channel=i.area.course_list_all'


class Main:
    def __init__(self):
        self.start_time = time.strftime("%m-%d %H:%M:%S")
        self.lessons = None  # 课程列表
        self.options = Options()
        self.options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        self.wd = Chrome(service=Service('chromedriver.exe'), options=self.options)
        self.wd.implicitly_wait(3)
        self.refresh_lessons()
        self.wd.refresh()  # 刷新页面，等3秒
        print("正在执行初始化...", end="\r")
        time.sleep(3)

    def refresh_lessons(self):
        """
        页面刷新后,要重新载入lesson
        :return:
        """
        self.lessons = self.wd.find_elements(By.CSS_SELECTOR,
                                             '#app > div > div.app-main_.appMain > div.courseActionLesson > div.courseAction_lesson_left.lesson_left > div.list > div > ul > li > ul > li.detail > ul > li > div > span')

    def get_title(self):
        """
        获取页面标题
        :return: 页面标题
        """
        title_ele = self.wd.find_element(By.CSS_SELECTOR,
                                         '#app > div > div.app-main_.appMain > div.courseActionLesson > div.lesson_rightcon > div.lesson_right.content_right > div.hover_overflow > div > p')
        title = title_ele.get_property("innerText")
        return title

    def judge_pause(self):
        """
        判断视频是否暂停,若检测到暂停，就点击播放
        :return:
        """
        status_ele = self.wd.find_element(By.CSS_SELECTOR,
                                          '#qa-video-wrap > div > xt-wrap > xt-controls > xt-inner > xt-playbutton > xt-tip')
        status = status_ele.get_attribute("innerText")
        play_btn = self.wd.find_element(By.CSS_SELECTOR, '#qa-video-wrap > div > xt-wrap > xt-bigbutton > button')
        if status == "播放":
            play_btn.click()

    def move_to_start(self):
        """
        将视屏从头播放
        :return:
        """
        video_ele = self.wd.find_element(By.CSS_SELECTOR, 'div video.xt_video_player')
        self.wd.execute_script(f'arguments[0].currentTime = 0;', video_ele)

    def watch(self, lesson_index, lessons_num):
        """
        观看每一个视频
        :param lesson_index: 视频索引
        :param lessons_num: 视频总数量
        :return:
        """
        time.sleep(1)
        self.move_to_start()
        total_time = self.get_total_time()
        title = self.get_title()
        while total_time == 0:  # 有时候总时间未加载完毕，重复加载
            total_time = self.get_total_time()
            title = self.get_title()
        while True:
            if self.get_cur_time() == total_time:
                print("当前视频播放完成!", end="\r")
                time.sleep(3)
                self.wd.refresh()
                break
            time.sleep(1)

            print(
                '正在学习"{}",当前视频进度:{:.2f}%,视频总进度：{}/{},开始时间：{}，当前时间：{}'.format(title,
                                                                                                    self.get_cur_time() / total_time * 100,
                                                                                                    lesson_index + 1,
                                                                                                    lessons_num,
                                                                                                    self.start_time,
                                                                                                    time.strftime(
                                                                                                        "%m-%d %H:%M:%S")),
                end="\r")
            self.judge_pause()  # 处理暂停问题

    def get_cur_time(self):
        """
        获取当前视频时间
        :return: 当前视频时间
        """
        cur_element = self.wd.find_element(By.CSS_SELECTOR,
                                           '#qa-video-wrap > div > xt-wrap > xt-controls > xt-inner > xt-time > span.white')
        curr_time = cur_element.get_attribute("innerText")
        hours, minutes, seconds = map(int, curr_time.split(':'))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    def get_total_time(self):
        """
        获取视频总时间
        :return: 视频总时间
        """
        cur_element = self.wd.find_element(By.CSS_SELECTOR,
                                           '#qa-video-wrap > div > xt-wrap > xt-controls > xt-inner > xt-time > span:nth-child(2)')
        curr_time = cur_element.get_attribute("innerText")
        hours, minutes, seconds = map(int, curr_time.split(':'))
        return hours * 3600 + minutes * 60 + seconds

    def run(self):
        """
        主程序
        :return:
        """
        outer_divs = self.wd.find_elements(By.CSS_SELECTOR,
                                           '#app > div > div.app-main_.appMain > div.courseActionLesson > div.courseAction_lesson_left.lesson_left > div.list > div > ul > li > ul > li.detail > ul > li > div')

        for lesson_index in range(len(outer_divs)):
            flag = outer_divs[lesson_index].find_elements(By.CSS_SELECTOR,
                                                          'i.iconfont.percentFull')  # 根据是否由完成的icon判读视频完成情况
            if len(flag) != 0:  # finished
                print(
                    f'跳过已完成课程{lesson_index + 1},开始时间：{self.start_time}，当前时间：{time.strftime("%m-%d %H:%M:%S")}',
                    end="\r")
            else:  # unfinished
                self.refresh_lessons()  # 刷新课程列表，将每节课的开始按钮放入self.lessons
                lesson = self.lessons[lesson_index]  # 选择第lesson_index节课
                self.wd.execute_script("arguments[0].click();", lesson)  # 点击课程
                time.sleep(3)  # 点击课程后等3秒
                self.watch(lesson_index, len(self.lessons))  # 若视频未完成就观看
                time.sleep(3)  # 看完等待3秒

    def final_check(self):
        """
        视频播放完成后，要重新检测一下
        :return:
        """
        print("刷新页面，重新检查课程完成情况......", end="\r")
        self.wd.refresh()  # 刷新页面
        self.run()  # 重新运行
        print(f'视频全部完成!开始时间：{self.start_time}，当前时间：{time.strftime("%m-%d %H:%M:%S")}', end="\r")


if __name__ == '__main__':
    m = Main()
    m.run()
    m.final_check()
