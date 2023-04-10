"""
工具类模块
"""

import json
import os
import re
from datetime import datetime as dt
from datetime import timedelta
from json import dumps, loads
from random import uniform
from time import sleep

from bs4 import Tag

_DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
__URL_FIND__ = {
    "jdcgw": [47, "https://www.plap.cn/index/selectsumBynews.html?", ],
    "qjc": [24, "http://www.weain.mil.cn/"],
    "zgzf": [25, "http://search.ccgp.gov.cn"]
}
# ASCII 码转中文
__URL_REPLACE__ = {
    "jdcgw": {
        "%25E7%2589%25A9%25E8%25B5%2584": "物资",
        "%25E5%2585%25AC%25E5%25BC%2580%25E6%258B%259B%25E6%25A0%2587": "公开招标",
        "%25E9%2582%2580%25E8%25AF%25B7%25E6%258B%259B%25E6%25A0%2587": "邀请招标",
        "%25E7%25AB%259E%25E4%25BA%2589%25E6%2580%25A7%25E8%25B0%2588%25E5%2588%25A4": "竞争性谈判"
    },
    "qjc": {
        "%E5%85%AC%E5%BC%80%E6%8B%9B%E6%A0%87": "公开招标",
        "%E9%82%80%E8%AF%B7%E6%8B%9B%E6%A0%87": "邀请招标",
        "%E7%AB%9E%E4%BA%89%E6%80%A7%E8%B0%88%E5%88%A4": "竞争性谈判"
    },
    "zgzf":{
        "&dbselect=bidx": "",
        "&bidSort=0": "",
        "&displayZone=": "",
        "&zoneId=": "",
        "&pppStatus=0": "",
        "&agentName=": "",
        "&buyerName=": "",
        "&projectId=": ""
    }
}


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


def bs_deep_get(s_tag: Tag, rule) -> Tag or None:
    """
    Args:
        s_tag (bs4.element.Tag): 要检索的tag
        rule (str, list): 检索规则,用 "." 分开
    Returns:
        tag (bs4.element.Tag)
    """
    if isinstance(rule, str):
        rule = rule.split(".")
    assert type(rule) is tuple or list
    if s_tag is None:
        return None
    if not rule:
        return s_tag
    return bs_deep_get(s_tag.find(rule[0]), rule[1:])


def date_now_s(file_new=False, format=None) -> str:
    """ 返回当前日期
    Args:
        file_new (bool): 为True时将-变为_
    """
    if format is not None:
        return dt.now().strftime(format)
    if file_new:
        return dt.now().strftime('_%Y_%m_%d-%H_%M_%S')
    else:
        return dt.now().strftime(_DATE_TIME_FORMAT)


def date_days(change_days=0, format=None):
    """ 返回当前日期,仅到日
    Args:
        change_days (int): 增加或减少的天数
    Retruns:
        str : 返回计算后日期的字符串
    """
    if not format:
        format = _DATE_TIME_FORMAT
    return (dt.now() + timedelta(days=change_days)).strftime(format)


def get_time_add(time_base=None, delay="1h"):
    """
    Args:
        min:
        time_base:
    Returns:
        time_base + time_add
    """
    time_base = dt.strptime(time_base) if time_base else dt.now()
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
    return (time_base + time_add).strftime('%Y-%m-%d %H:%M:%S')


def t1_slow_than_t2(time1, time2) -> bool:
    """ 若time1 慢于 time2(time1在time2后) 返回True, 否则返回 False
    """
    if dt.strptime(time1, _DATE_TIME_FORMAT) > \
            dt.strptime(time2, _DATE_TIME_FORMAT):
        return True
    return False


def read_json(file):
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


def url_to_filename(url: str):
    """
    将url 转换为可创建的文件名,会删除 https http www , 将 / 替换为( , 将所有后缀替换为html
    Args:
        url (str): 网址
    Returns:
        url (str): 转换后的网址,可作为文件名
    """
    # 将 / 替换成 空格 因为网址中不会有空格
    if len(url) > 100:  # 部分网址有可能过长, windows文件名不能超过179个字符
        for key, value in __URL_FIND__.items():
            if url[:value[0]] == value[1]:
                # url = url.replace(url[:value[0]], "")
                for ascii, chn in __URL_REPLACE__[key].items():
                    url = url.replace(ascii, chn)
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


def str_dict(output_dict: dict):
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


def creat_folder(file):
    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)


def jsdump(d, indent=2, ensure_ascii=False, sort_keys=False):
    """简化版json.dumps, 自带默认参数"""
    return json.dumps(d, indent=indent, ensure_ascii=ensure_ascii,
                      sort_keys=sort_keys)


def sleep_random(time_range: tuple = (2, 3), message: str = None):
    """ 在随机范围内sleep, 并带有提示, 默认为1.7秒到3秒内
    """
    from module.log import logger
    sleep_time = uniform(*time_range)
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


def time_difference_second(time1, time2):
    """获得时间差,单位为秒,返回 time1 - time2"""
    return (dt.strptime(time1, "%Y-%m-%d %H:%M:%S") -
            dt.strptime(time2, "%Y-%m-%d %H:%M:%S")).seconds


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


def reset_task(settings: dict, task_name: dict, json_file=""):
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


def reset_json_file(json_file):
    """ 重置一个json文件task.list里所有任务"""
    settings = read_json(json_file)
    for task_name in settings["task"]["test"]:
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
    reset_json_file("./bid_settings/bid_settings.json")
    pass
