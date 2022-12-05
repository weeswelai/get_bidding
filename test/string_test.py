"""
TODO 试试前缀树? 试试保存前缀树的变量到本地
测试匹配速度
"""
import _ctypes
import pickle
import os

from module.utils import *
from module.bid_judge_content import title_trie

str_t = """['吉林大学原子层沉积系统采购项目招标公告', '2022-11-14', '/zhwzb/391052.jhtml', '货物']
['吉林大学高精度磁学测量系统采购项目招标公告', '2022-11-14', '/zhwzb/391051.jhtml', '货物']
['吉林大学电子探针显微分析仪采购项目招标公告', '2022-11-14', '/zhwzb/391050.jhtml', '货物']
['吉林大学高分辨X射线衍射仪（含摇摆曲线测量组件）采购项目招标公告', '2022-11-14', '/zhwzb/391049.jhtml', '货物']
['广东医科大学附属医院麻醉手术中心设备采购项目（一）招标公告', '2022-11-14', '/zhwzb/391048.jhtml', '货物']
['磁化偏滤器部件测试加速系统采购-竞争性谈判采购公告', '2022-11-14', '/zhwzb/391047.jhtml', '货物']
['哈尔滨音乐学院食堂大宗食品采购项目（二次）-招标公告', '2022-11-14', '/zhwzb/391045.jhtml', '货物']
['吉林大学全自动酶联免疫分析系统采购项目招标公告', '2022-11-14', '/zhwzb/391040.jhtml', '货物']
['三维光学检测系统-招标公告', '2022-11-14', '/zhwzb/391039.jhtml', '货物']
['佛山烟草物流配送中心2022年分拣、仓储备件采购项目招标公告', '2022-11-14', '/zhwzb/391038.jhtml', '货物']
['自动配料改进版化学试验测试-询价采购公告', '2022-11-14', '/zhwzb/391031.jhtml', '货物']"""

# input 有四种形式 多行字符串,单行字符串 一维数组， 多维数组

if __name__ == "__main__":
    ConsoleTest = 0  # 控制台调试,在代码最下方,需要添加断点
    ReadFromStr = 0  # 测试字符串 存进前缀树
    LoadFromFile = 0  # 将文本文件的内容存进前缀树中
    SaveLocal = 0  # 保存前缀树到二进制文件中
    Test_search_all = 1  # 测试检索整个字符串,返回符合的匹配项

    # 将word 存进前缀树
    if ReadFromStr:
        word_insert = "声：光 测 试"
        title_trie.insert_from_str(word_insert)

    # 将文本文件的内容存进文件树中
    if LoadFromFile:
        f_r = "./test/前缀树.txt"
        title_trie.init_from_file(f_r)

    # 保存前缀树到文件中
    if SaveLocal:
        save_file = "./test/tile_tire_t.json"
        title_trie.save_local(save_file)

    # 测试检索整个字符串,返回符合的匹配项
    if Test_search_all:
        Test_search_all_fromFile = 0  # 从文件中查找
        Test_search_all_fromStr = 0  # 从字符串中查找
        Test_search_all_fromStrLines = 1  # 从多行字符串中查找
        # 多行字符串转list
        if Test_search_all_fromStrLines:
            l_t = str_t.split("\n")
            for idx, line in enumerate(l_t, start=1):
                line = eval(line)
                result = title_trie.search_all(line[0])
                if result:
                    logger.info(f"get {result} from {line[0]} line: {idx}")
        elif Test_search_all_fromStr:
            str_t2 = "哈尔滨音乐学院led食堂大宗食品面板采购项目（二次）-招标公告"
            logger.info(
                f"get words: {title_trie.search_all(str_t2)} from {str_t2}")
        elif Test_search_all_fromFile:
            file = ""
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    logger.info(title_trie.search_all(line))
    # 控制台调试
    if ConsoleTest:
        _ = input()
