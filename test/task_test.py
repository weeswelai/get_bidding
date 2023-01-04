"""
单个任务的测试
需求: 测试一个state
该state 可以从特定网址开始
从头测试一个 task
测试state可从特定网址开始
"""

import traceback
from shutil import copyfile

from module.log import logger
from module.task import BidTask
from module.utils import *

# 配置文件
SETTINGS_DEFAULT = "./bid_settings/bid_settings_default.json"
SETTINGS_JSON = "./bid_settings/bid_settings.json"
SETTINGS_JSON_TEST = "./bid_settings/bid_settings_test.json"
if not os.path.exists(SETTINGS_JSON_TEST):
    if os.path.exists(SETTINGS_JSON):
        copyfile(SETTINGS_JSON, SETTINGS_JSON_TEST)
    else:
        copyfile(SETTINGS_DEFAULT, SETTINGS_JSON_TEST)

settings = read_json(SETTINGS_JSON_TEST)

# 任务初始化
task_name = "jdcg"
bid_task = BidTask(settings[task_name], task_name, test=True)

#任务开关
test_task = 1  # 测试一个任务
test_state = 0  # 测试任务里一个过程
state_reset = 0  # 重置任务设置, 包括end_rule 和 complete状态

def save():
    save_json(settings, SETTINGS_JSON_TEST)

def reset(state_idx):
    # if reset:
    default = settings["default"]["state1"]
    url = bid_task.settings[state_idx]["url"]
    bid_task.settings[state_idx] = default.copy()
    bid_task.settings[state_idx]["url"] = url


def state_run():
    """完成task里一个过程"""
    while bid_task.process_next_list_web():
        save()
        sleep_random(message="you can use 'Ctrl  C' stop now")
    save()


# 任务过程
try:
    # 完成一个task
    if test_task:
        
        # task的 stateQueue重置
        bid_task.restart()
        
        # 若开启重置任务, 会把stateQueue里每个过程都重置
        if state_reset:
            for state in bid_task.settings["stateQueue"]:
                reset(state)
        save()

        # 完成task
        while bid_task.init_state():
            state_run()


    state_idx = "公开招标"
    start_url = "https://www.plap.cn/index/selectsumBynews.html?page=3&id=3&twoid=24&title=&productType=&productTypeName=&tab=%25E7%2589%25A9%25E8%25B5%2584&lastArticleTypeName=%25E5%2585%25AC%25E5%25BC%2580%25E6%258B%259B%25E6%25A0%2587&publishStartDate=&publishEndDate="
    
    # task 和 state 只测一个
    # 完成task里一个过程
    if not test_task and test_state:
        bid_task.settings["stateWait"] += bid_task.settings["stateQueue"]
        bid_task.settings["stateQueue"] = [state_idx]

        # 若启用重置任务设置
        if state_reset:
            reset(state_idx)
        if start_url:
            url = bid_task.settings[state_idx]["url"]
            bid_task.settings[state_idx]["url"] = start_url
            bid_task.settings[state_idx]["url_old"] = url
        save()
        bid_task.init_state()
        state_run()

except Exception:
    save()
    logger.error(traceback.format_exc())


    
    


