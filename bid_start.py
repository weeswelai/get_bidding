"""
启动任务
读取配置, 初始化运行环境
初始化 任务调度对象，网页浏览对象， 读取配置文件，将配置文件和网页浏览对象交给任务调度对象
"""


# import module.bid_task as bid_task
# import module.get_url as get_url
# from module.bid_web_brows import web_brows
from time import sleep
from module.bid_log import logger
from module.bid_task import *
from module.utils import *

# 读取配置json
# settings_json = "./bid_settings/bid_settings_t.json"
settings_json = "./bid_settings/bid_settings_t_2022_11_30-13_37_32_358.json"
logger.info(f"load json settings file")

runFlag = True
testFlag = False
fileTest = True

task_continue = 0
web_brows_continue = 0
# 初始化任务
# try:
#     bidTaskManager = TaskManager(settings_json,
#                                  creat_new=(True if test_flag else False))
# except Exception as e:
#     logger.error(e)
bidTaskManager = TaskManager(settings_json,
                             creat_new=(True if testFlag else False))

# TODO
# 写一个死循环,任务调度器不断读取任务队列，进行翻页，读取网页内容
if __name__ == "__main__":
    # try:
    if runFlag:
        while task_continue < 1:
            # bidTaskManager.start_task()
            bidTaskManager.build_new_task()
            while web_brows_continue < 2:
                # 创建项目列表页面,或进行翻页
                bidTaskManager.build_list_pages_brows()
                # 打开项目列表网址
                bidTaskManager.open_list_url()
                # 获得网页招标项目list,完成后有 bid_list
                bidTaskManager.get_list_from_list_web_html()
                # TODO 判断当前list
                bidTaskManager.process_bid_list()
                # TODO 依次打开match_list中的网页, 爬取、判断内容
                sleep(3)  # TODO 后期换成定时器
                web_brows_continue += 1
            task_continue += 1