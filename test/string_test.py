"""
TODO 试试前缀树? 试试保存前缀树的变量到本地
测试匹配速度
"""

from module.utils import *
from module.judge_content import titleTrie
from module.log import logger

str_t = """"""

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
        titleTrie.insert_from_str(word_insert)

    # 将文本文件的内容存进文件树中
    if LoadFromFile:
        f_r = "./test/前缀树.txt"
        titleTrie.init_from_file(f_r)

    # 保存前缀树到文件中
    if SaveLocal:
        save_file = "./test/tile_tire_t.json"
        titleTrie.save_local(save_file)

    # 测试检索整个字符串,返回符合的匹配项
    if Test_search_all:
        Test_search_all_fromFile = 1  # 从文件中查找
        Test_search_all_fromStr = 0  # 从字符串中查找
        Test_search_all_fromStrLines = 0  # 从多行字符串中查找
        # 多行字符串转list
        if Test_search_all_fromStrLines:
            l_t = str_t.split("\n")
            for idx, line in enumerate(l_t, start=1):
                line = eval(line)
                result = titleTrie.search_all(line[0])
                if result:
                    logger.info(f"get {result} from {line[0]} line: {idx}")
        elif Test_search_all_fromStr:
            str_t2 = "哈尔滨音乐学院led食堂大宗食品面板采购项目（二次）-招标公告"
            logger.info(
                f"get words: {titleTrie.search_all(str_t2)} from {str_t2}")
        elif Test_search_all_fromFile:
            file = "./data/bid_list_zzlh.txt"
            output = "./test/string_test.txt"
            if output:
                out = open(output, "w", encoding="utf-8")
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    lineMatch = line.split(";")[0]
                    # logger.info(titleTrie.search_all(line))
                    if output:
                        match = titleTrie.search_all(lineMatch)
                        if match:
                            out.write(f"{match}, {line}")
            if output:
                out.close()
    # 控制台调试
    if ConsoleTest:
        _ = input()
