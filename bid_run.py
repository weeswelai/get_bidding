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
import traceback
from time import sleep

from module.log import logger
from module.task_manager import TaskManager

# 读取配置json
SETTINGS_DEFAULT = "./bid_settings/bid_settings_default.json"
SETTINGS_JSON = "./bid_settings/bid_settings.json"
if not os.path.exists(SETTINGS_JSON):
    shutil.copyfile(SETTINGS_DEFAULT, SETTINGS_JSON)
runFlag = True
newFlag = False
# 初始化任务
bidTaskManager = TaskManager(SETTINGS_JSON,
                             creat_new=(True if newFlag else False))

if __name__ == "__main__":
    if runFlag:
        try:
            bidTaskManager.loop()
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            bidTaskManager.exit()
            
