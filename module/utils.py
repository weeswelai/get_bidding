"""
工具类模块
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from random import uniform
from urllib.parse import unquote

from bs4 import Tag

# json or file

def deep_set(d: dict, keys: list or str, value):
    """
    from https://github.com/LmeSzinc/AzurLaneAutoScript/blob/master/module/config/utils.py
    Set value into dictionary safely, imitating deep_get().
    """
    if isinstance(keys, str):
        keys = keys.split('.')
    assert type(keys) is list
    if not keys:
        return value
    if not isinstance(d, dict):
        d = {}
    d[keys[0]] = deep_set(d.get(keys[0], {}), keys[1:], value)
    return d


def deep_get(d: dict, keys: list or str, default=None):
    """
    Get values in dictionary safely.
    https://stackoverflow.com/questions/25833613/safe-method-to-get-value-of-nested-dictionary

    Args:
        d (dict):
        keys (str, list): Such as `Scheduler.NextRun.value`
        default: Default return if key not found.

    Returns:

    """
    if isinstance(keys, str):
        keys = keys.split('.')
    assert type(keys) is list
    if d is None:
        return default
    if not keys:
        return d
    return deep_get(d.get(keys[0]), keys[1:], default)


def save_json(data, json_file, indent=2, logger=None):
    """ 覆写json文件
    Args:
        data (dict): 保存的数据
        json_file (str): 保存的json文件路径
        indent (int): json 由dict转换成str的间隔,默认为2
        creat_new (bool): 是否保存为新文件,默认为False
    Returns:
        json_file (str): 保存的json文件路径
    """
    create_folder(json_file)

    with open(json_file, "w", encoding="utf-8") as json_file_w:
        write_data = json.dumps(data, indent=indent, ensure_ascii=False,
                                sort_keys=False, default=str)
        json_file_w.write(write_data)
    if logger:
        logger.info(f"save {json_file}")


def jsdump(d, indent=2, ensure_ascii=False, sort_keys=False) -> str:
    """简化版json.dumps, 自带默认参数, dict -> str"""
    return json.dumps(d, indent=indent, ensure_ascii=ensure_ascii,
                      sort_keys=sort_keys)


def create_folder(file):
    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)


def save_file(file, data, mode="w", bytes=False):
    """ 保存文件
    """
    create_folder(file)
    if bytes:
        with open(file, "wb") as f:
            f.write(data)
    else:
        with open(file, mode, encoding="utf-8") as f:
            f.write(str(data))


# time
RUN_TIME_START = "2023-01-01 00:00:00"  # 默认下次运行时间
_DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def time2str(time: timedelta, format=None) -> str:
    if format:
        return datetime.strftime(time, format)
    return datetime.strftime(time, _DATE_TIME_FORMAT)


def str2time(time: str, format=None) -> datetime:
    if format:
        return datetime.strptime(time, format)
    return datetime.strptime(time, _DATE_TIME_FORMAT)


def date_now_s(file_new=False, format=None) -> str:
    """ 返回当前日期
    Args:
        file_new (bool): 为True时将-变为_
    """
    if format is not None:
        return datetime.now().strftime(format)
    if file_new:
        return datetime.now().strftime('_%Y_%m_%d-%H_%M_%S')
    else:
        return datetime.now().strftime(_DATE_TIME_FORMAT)


def date_days(change_days=0, format=None):
    """ 返回当前日期,仅到日
    Args:
        change_days (int): 增加或减少的天数
    Retruns:
        str : 返回计算后日期的字符串
    """
    if not format:
        format = _DATE_TIME_FORMAT
    if format == "day":
        format = "%Y-%m-%d"
    return (datetime.now() + timedelta(days=change_days)).strftime(format)


def get_time_add(delay="1h") -> timedelta:
    """
    Args:
        delay(str, int)
    Returns:
        time_base + time_add
    """
    if isinstance(delay, int):
        time_add = timedelta(minutes=delay)
    if isinstance(delay, str):
        time_, unit = int(delay[:-1]), delay[-1]
        if unit == "h":
            time_add = timedelta(hours=time_)
        elif unit == "d":
            time_add = timedelta(days=time_)
        elif unit == "m":
            time_add = timedelta(minutes=time_)
    return time_add


def sleep_random(time_range: tuple = (2, 3), message: str = None):
    """ 在随机范围内sleep, 并带有提示, 默认为1.7秒到3秒内
    """
    from module.log import logger
    sleep_time = round(uniform(*time_range), 3)
    if message:
        print(f"wait {sleep_time} s, {message}")
    logger.info(f"sleep {sleep_time}")
    sleep_idx = int(sleep_time)
    for idx in range(1, sleep_idx + 1):
        print(f"sleep {idx} now")
        time.sleep(1)
    print(f"sleep {sleep_time} now")
    time.sleep(sleep_time - sleep_idx)
    print("sleep end")


def time_difference(time1, time2, unit="second"):
    """获得时间差,单位为秒,返回 time1 - time2
    Args:
        unit (str): second or day 要求格式 "%Y-%m-%d %H:%M:%S"
    Returns:
        (int): 若 unit == second 返回秒的差值
               若 unit == day    返回日的差值
    """
    dif = datetime.strptime(time1, "%Y-%m-%d %H:%M:%S") - \
          datetime.strptime(time2, "%Y-%m-%d %H:%M:%S")
    if dif.days < 0:
        return 1
    if unit == "second":
        return dif.seconds
    elif unit == "day":
        return dif.days


def url_to_filename(url: str):
    """
    将url 转换为可创建的文件名,会删除 https http www , 将 / 替换为( , 将所有后缀替换为html
    Args:
        url (str): 网址
    Returns:
        url (str): 转换后的网址,可作为文件名
    """
    # 将 / 替换成 空格 因为网址中不会有空格
    
    url, url_params = url.split("?") if "?" in url else (url, "")
    if url_params:
        params_list =url_params.split("&")
        for p in params_list:
            if "=" not in p:
                continue
            k, v = p.split("=")
            if v and "%" in v:
                v = unquote(v, "utf-8") if "plap" in url else v
                v = unquote(v, "utf-8")
                url_params = url_params.replace(p, f"{k}={v}")
            else:
                url_params = url_params.replace(f"&{p}", "")
        url = f"{url}?{url_params}"
    if url.find("//www") > 0:
        url = url[url.find(".") + 1:]
    elif url.find("//") > 0:
        url = url[url.find("//") + 2:]
    url = url.replace("/", " ").replace("?", " ").replace(":", " ")
    if url[-5:] != ".html":
        url = f"{url}.html"
    return url


def init_re(re_rule, flag=re.S):
    """ 返回编译好的正则表达式
    Args:
        re_rule (dict or str): 
        flag (int): 默认为16, "." 将选取换行符, 16 = re.S
    """
    if isinstance(re_rule, str):
        return re.compile(re_rule)
    elif isinstance(re_rule, dict):
        if isinstance(re_rule["rule_option"], int):
            flag = re_rule["rule_option"]
        return re.compile(re_rule["re_rule"], flags=flag)
    elif re_rule is None:
        return None


# reset
"""
1. 读取json,重置可选任务的时间或bid_task, 时间和 bid_task 分别可选
2. 重置一个任务的时间或bid_task, 时间和 bid_task 分别可选
3. 重置一个bid_task的时间或将其状态清空
"""

def _set_time(d: dict, name: str = None, time=""):
    task = d[name] if name else d
    task["nextRunTime"] = time


def _clear_bid_task(d, keys=None):
    """ 重置一个 bid_task  如 zzlh的 货物 """
    if not keys:
        keys = ("newestBid", "interruptUrl", "interruptBid", "stopBid")
    for key in keys:
        if isinstance(d[key], str):
            d[key] = ""
            continue
        for k in d[key]:
            d[key][k] = ""
    d["state"] = ""
    _set_time(d)


def reset_task(task_d: dict, name="", clear_bid=False, time=""):
    """ 重置一个任务的 nextRunTime 和 bid_task """
    task = task_d[name] if name else task_d
    time = RUN_TIME_START if isinstance(time, bool) else time
    if time or time == "":
        _set_time(task, time=time)
    for bid_task in  task["TaskList"]:
        if time or time == "":
            _set_time(task[bid_task], time=time)
        if clear_bid:
            _clear_bid_task(task[bid_task])


def clear_json_file(json_file, task="", clear_bid=False, time=None):
    """ 重置一个json文件task.list里所有任务"""
    read_file = False
    if isinstance(json_file, dict):
        json_d = json_file    
    else:
        read_file = True
        with open(json_file, "r", encoding="utf-8") as f:
            json_d = json.loads(f.read())
    if task:
        reset_task(json_d, task, clear_bid, time)
    else:
        for name in json_d["task"]["list"]:
            reset_task(json_d, name, clear_bid, time)
    if read_file:
        save_json(json_d, json_file)


def copy_settings(old, new, new_file_name=""):
    with open(old, "r", encoding="utf-8") as old_file,\
         open(new, "r", encoding="utf-8") as new_file:
        old_json = json.loads(old_file.read())
        new_json = json.loads(new_file.read())
    # "task"
    new_json["task"] = old_json["task"]
    # BidTask
    for name in old_json["task"]["list"]:
        for task in old_json[name]:
            if task in ("task", "BidTag", "brows", "Bid"):
                continue
            if task == "OpenConfig":
                for config in ("headers", "cookies"):
                    new_json[name][task][config] = old_json[name][task][config]
                continue
            new_json[name][task] = old_json[name][task]
    new_file_name = new_file_name or new
    save_json(new_json, new_file_name)


# cookies
def cookie_str_to_dict(cookies: str):
    if not isinstance(cookies, str) or cookies == {}:
        return cookies
    cookie_dict = {}
    for c in cookies.split(";"):
        if c.strip():
            key, value = c.strip().split("=", 1)
            cookie_dict[key] = value
    return cookie_dict


if __name__ == "__main__":
    # 本模块测试
    # test code
    # clear_json_file("./bid_settings/bid_settings_default.json", clear_bid=True, set_time=True)
    clear_json_file("./bid_settings/bid_settings.json", task="zgzf", time="")
    # copy_settings("./bid_settings/bid_settings.json", "./bid_settings/bid_settings_newClass.json")
    pass
