"""
启动任务
读取配置, 初始化运行环境
初始化 任务调度对象，网页浏览对象， 读取配置文件，将配置文件和网页浏览对象交给任务调度对象
"""

from time import sleep

from module.bid_log import logger
from module.bid_task import TaskManager
from module.utils import *

# 读取配置json
settings_json = "./bid_settings/bid_settings_t.json"
logger.info(f"load json settings file from {settings_json}")

runFlag = True
newFlag = False
fileTest = True

task_continue = 0
web_brows_continue = True
# 初始化任务
bidTaskManager = TaskManager(settings_json,
                             creat_new=(True if newFlag else False))

# TODO
# 写一个死循环,任务调度器不断读取任务队列，进行翻页，读取网页内容
if __name__ == "__main__":
    # try:
    if runFlag:
        start_name = bidTaskManager.queue[0]
        while task_continue < 1:
            state = ""
            # 判断状态是否开始新任务
            if bidTaskManager.state in (None, "complete"):
                # 构建新任务
                bidTaskManager.new_task()
            # 任务执行
            state = bidTaskManager.task_run()
            # 判断执行结果
            if state == "complete":
                # 任务完成
                state = ""
                if start_name == bidTaskManager.task_complete():
                    sleep(30)
            
            task_continue += 1
