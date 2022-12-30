"""
启动任务
读取配置, 初始化运行环境
初始化 任务调度对象，网页浏览对象， 读取配置文件，将配置文件和网页浏览对象交给任务调度对象
任务调度模块
功能为
 打开 .json配置文件
 判断时间，判断访问频率是否合适
 调度网页的打开、项目列表页面的翻页
"""
import os
import shutil
from time import sleep

from module.task_manager import TaskManager

# 读取配置json
settings_default = "./bid_settings/bid_settings_default.json"
settings_json = "./bid_settings/bid_settings.json"
if not os.path.exists(settings_json):
    shutil.copyfile(settings_default, settings_json)
runFlag = True
newFlag = False
# 初始化任务
bidTaskManager = TaskManager(settings_json,
                             creat_new=(True if newFlag else False))

# TODO
# 写一个死循环,任务调度器不断读取任务队列，进行翻页，读取网页内容
if __name__ == "__main__":
    if runFlag:
        try:
            bidTaskManager.loop()
        except KeyboardInterrupt:
            bidTaskManager.exit()