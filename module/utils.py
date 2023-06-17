"""
工具类模块
"""

import json
import os
import re
from datetime import datetime, timedelta
from json import dumps, loads
from random import uniform
from time import sleep
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


def read_json(file) -> dict:
    """ 读取json文件,并返回dict
    Args:
        file (str): josn文件路径
    Returns:
        dict : json.loads转换的dict
    """
    from module.log import logger
    with open(file, "r", encoding="utf-8") as settings_json_r:
        f_read = settings_json_r.read()
        logger.info(f"read {file}")
        return loads(f_read)


def save_json(data, json_file, indent=2):
    """ 覆写json文件
    Args:
        data (dict): 保存的数据
        json_file (str): 保存的json文件路径
        indent (int): json 由dict转换成str的间隔,默认为2
        creat_new (bool): 是否保存为新文件,默认为False
    Returns:
        json_file (str): 保存的json文件路径
    """
    from module.log import logger
    creat_folder(json_file)

    with open(json_file, "w", encoding="utf-8") as json_file_w:
        write_data = dumps(data, indent=indent, ensure_ascii=False,
                           sort_keys=False, default=str)
        json_file_w.write(write_data)
    logger.info(f"save {json_file}")


def jsdump(d, indent=2, ensure_ascii=False, sort_keys=False) -> str:
    """简化版json.dumps, 自带默认参数, dict -> str"""
    return json.dumps(d, indent=indent, ensure_ascii=ensure_ascii,
                      sort_keys=sort_keys)


def creat_folder(file):
    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)


def save_file(file, data, mode="w", bytes=False):
    """ 保存文件
    """
    creat_folder(file)
    if bytes:
        with open(file, "wb") as f:
            f.write(data)
    else:
        with open(file, mode, encoding="utf-8") as f:
            f.write(str(data))


# time

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
        min:
        time_base:
    Returns:
        time_base + time_add
    """
    if isinstance(delay, int):
        time_add = timedelta(minutes=delay)
    if isinstance(delay, str):
        time_ , unit = int(delay[:-1]), delay[-1]
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
        sleep(1)
    print(f"sleep {sleep_time} now")
    sleep(sleep_time - sleep_idx)
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


def t1_slow_than_t2(time1, time2) -> bool:
    """ 若time1 慢于 time2(time1在time2后) 返回True, 否则返回 False
    """
    if datetime.strptime(time1, _DATE_TIME_FORMAT) > \
            datetime.strptime(time2, _DATE_TIME_FORMAT):
        return True
    return False


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


def str_list(output_list, level=1, add_idx=False):
    """
    打印多维list
    Args:
        output_list:
        level
        add_idx
    """
    output = ""

    if level == 0:
        output = f"{output}{str(output_list)}"
    elif level == 1:
        if add_idx:
            for idx, li in enumerate(output_list, start=1):
                output = f"{output}{idx}: {str(li)}\n"
        else:
            for li in output_list:
                output = f"{output}{str(li)}\n"
    # elif level == 2:
    #     for li in output_list:
    #         for i in li:
    #             output = f"{output}{i}"
    #         output = f"{output}\n"
    return output, len(output)


def dict2str(output_dict: dict):
    data = "  "
    for key, value in output_dict.items():
        data = f"{data}{key}: {value}\n  "
    return data.rstrip()


def re_options_print(options):
    """
    打印 re.S re.M 的值
    Args:
        options (re.options): S M
    """
    from module.log import logger
    logger.info(int(eval(f"re.{options}")))


def init_re(re_rule, flag=16):
    """ 返回编译好的正则表达式
    Args:
        re_rule (dict or str): 
        flag (int): 默认为16, "." 将选取换行符, 16 = re.S
        re.S 的值 可通过 utils.re_options_print 打印
    """
    if isinstance(re_rule, str):
        return re.compile(re_rule)
    elif isinstance(re_rule, dict):
        if isinstance(re_rule["rule_option"], int):
            flag = re_rule["rule_option"]
        return re.compile(re_rule["re_rule"], flags=flag)
    elif re_rule is None:
        return None


def reset_state(settings, key, json_file=""):
    """ 重置一个 state  如 zzlh的'货物'"""
    if isinstance(settings, str) and not json_file:
        json_file = settings
        settings = read_json(settings)
    url = deep_get(settings, f"{key}.url")
    deep_set(settings, key, settings["default"]["state1"].copy())
    deep_set(settings, f"{key}.url", url)
    if json_file:
        save_json(settings, json_file)


def reset_task(settings: dict, task_name: str, json_file=""):
    """ 重置一个任务的nextRunTime, newest interrupt end_rule"""
    if isinstance(settings, str) and not json_file:
        json_file = settings
        settings = read_json(settings)
    PageQueue = settings[task_name]["PageQueue"]
    PageWait = settings[task_name]["PageWait"]
    for _ in range(len(PageWait)):
        PageQueue.append(PageWait.pop(0))

    settings[task_name]["nextRunTime"] = ""
    for state in settings[task_name]["PageQueue"]:
        reset_state(settings, f"{task_name}.{state}")
    if json_file:
        save_json(json_file)


def reset_time(settings: dict, task_name: str):
    settings[task_name]["nextRunTime"] = ""


def reset_json_file(json_file, time=False):
    """ 重置一个json文件task.list里所有任务"""
    settings = read_json(json_file)
    for task_name in settings["task"]["list"]:
        if time:
            reset_time(settings, task_name)
        else:
            reset_task(settings, task_name)
    save_json(settings, json_file)


def cookie_str_to_dict(cookie: str):
    cookie_dict = {}
    for c in cookie.split(";"):
        if c.strip():
            key, value = c.strip().split("=", 1)
            cookie_dict[key] = value
    return cookie_dict


def cookie_dict_to_str(set_cookie: dict):
    cookie = ()
    for key, value in set_cookie.items():
        cookie += (f"{key}={value}",)
    return "; ".join(cookie).strip()


if __name__ == "__main__":
    # 本模块测试
    # test code
    reset_json_file("./bid_settings/bid_settings.json", time=True)
    pass
