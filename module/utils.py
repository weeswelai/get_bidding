"""
工具类模块
"""

import os
import datetime as dt
from json import loads, dumps
import re

from module.bid_log import logger


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


def date_now_s(file_new=False):
    """ 返回当前日期
    Args:
        file_new (bool): 为True时返回小数点精确到
    """
    if file_new:
        return dt.datetime.now().strftime('_%Y_%m_%d-%H_%M_%S_%f')[:-3]
    else:
        return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def date_days(change_days=0):
    """ 返回当前日期,仅到日
    Args:
        change_days (int): 增加或减少的天数
    Retruns:
        str : 返回计算后日期的字符串
    """
    return (dt.datetime.now() + dt.timedelta(days=change_days)).strftime(
        '%Y-%m-%d')


def read_json(file):
    """ 读取json文件,并返回dict
    Args:
        file (str): josn文件路径
    Returns:
        dict : json.loads转换的dict
    """
    with open(file, "r", encoding="utf-8") as settings_json_r:
        f_read = settings_json_r.read()
        logger.info(f"read {file}")
        return loads(f_read)


def save_json(data, json_file, indent=2, creat_new=False):
    """ 覆写json文件
    Args:
        data (dict): 保存的数据
        json_file (str): 保存的json文件路径
        indent (int): json 由dict转换成str的间隔,默认为2
        creat_new (bool): 是否保存为新文件,默认为False
    Returns:
        json_file (str): 保存的json文件路径
    """
    folder = os.path.dirname(json_file)
    if not os.path.exists(folder):
        os.mkdir(folder)

    if creat_new:  # 是否创建新文件保存
        json_file = f"{json_file.split('.json')[0]}{date_now_s(creat_new)}.json"

    with open(json_file, "w", encoding="utf-8") as json_file_w:
        write_data = dumps(data, indent=indent, ensure_ascii=False,
                           sort_keys=False, default=str)
        json_file_w.write(write_data)
    logger.info(f"save {json_file}")
    return json_file


def save_file(file, data):
    """ 保存文件
    """
    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)
    with open(file, "w", encoding="utf-8") as f:
        f.write(data)


def url_to_filename(url: str):
    """
    将url 转换为可创建的文件名,会删除 https http www , 将 / 替换为( , 将所有后缀替换为html
    Args:
        url (str): 网址
    Returns:
        url (str): 转换后的网址,可作为文件名
    """
    # 将 / 替换成 空格 因为网址中不会有空格
    url = url[url.find(".") + 1:].replace("/", " ")
    idx = url.rfind('.')  # 找到倒数第一个 . , 判断是否为html
    html_find = url[idx + 1:].find("html")  # 查找 html 位置

    if html_find < 0:  # 没有html
        url = f"{url}.html"
    elif html_find > 0:  # 另类的html后缀 , 如 jhtml
        url = f"{url[:idx]}.html"
    return url


def re_options_print(options):
    """
    打印 re.S re.M 的值
    Args:
        options (re.options): S M
    """

    print(int(eval(f"re.{options}")))


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

def init_re(re_rule):
    """ 返回编译好的正则表达式
    Args:
        re_rule (dict or str): 
    """
    if isinstance(re_rule, str):
        return re.compile(re_rule)
    elif isinstance(re_rule, dict):
        return re.compile(re_rule["re_rule"], flags=re_rule["rule_option"])

if __name__ == "__main__":
    # 本模块测试
    web_page = r"http://www.365trade.com.cn/zhwzb/390964.jhtml"
    logger.info(url_to_filename(web_page))
    pass
