"""
TODO
前缀树的错误插入检查
遍历得到的网页列表，判断每个名称是否符合要求
对招标项目网页的具体内容进行判断,截至时间、标书获取等
"""

import json
import pickle
from re import L
# 根据内存地址获得变量
from _ctypes import PyObj_FromPtr

from module.bid_log import logger
from module.utils import *

_get_p = PyObj_FromPtr


class BidTitleTrie:
    def __init__(self, read_file=""):
        self.child = {}
        if read_file:
            self.init_from_file(read_file)

    def insert_from_list(self, insert_list):
        if isinstance(insert_list[0], list):
            for l in insert_list:
                self._insert_from_list(l)
        else:
            self._insert_from_list(insert_list)

    def _insert_from_list(self, l_in: list):
        """  将列表中的所有字符串插入前缀树, 列表的形式为 [1,2,3],输入必须为3
        1: first关键词 字符开头 如 机
        2: first关键词 字符后可能的字符,用空格分隔 如 载 上, 与 1相连就是 机载 机上,
        2中每个字符最后一个=子dict添加"end"=True,表示结束
        3: second关键词 使用空格分隔, 3根据 1和2的组合插入进second树
        Examples:
            l_in : ["机","载 上","设备 系统"]
            l_in : ["l","ed","面板 屏"]
        Args:
            l_in (list): 要插入的字符串列表
        """
        first_aft = second = ""
        first = l_in[0].strip()
        if len(l_in) > 1:
            first_aft = l_in[1].strip().split(" ") if l_in[1].strip() else ""
            if len(l_in) > 2:
                second = l_in[2].strip().split(" ") if l_in[2].strip() else ""
        c_p = []  # 用于存second
        # 存first
        if first_aft:
            for word_aft in first_aft:  # 存first_after
                c_p.append(self._insert(f"{first}{word_aft.strip()}"))
        else:
            c_p = [self._insert(first)]
        # 存second
        if second:
            for s_p in c_p:
                for word_s in second:
                    self._insert(word_s, root=False, child_p=s_p)

    def insert_from_str(self, word_insert, split=""):
        """ 传入str, 使用分隔符将输入的多行字符串分隔成list, 再分别存入前缀树中
        需要保证list的每个元素为 "first:second" 形式
        Args:
            word_insert (str): 要插入的字符串
            split (str): 分隔符,默认为 "", 为 ""时不分割元素,将字符串变为单个元素的list
        """
        # 用输入的分隔符预处理,否则
        if split == "":
            word_list = word_insert.split(":")
            self.insert_from_list(word_list)
        else:
            word_list = word_insert.split(split)
            for l in word_insert:
                self.insert_from_list()

    def init_from_file(self, file_read="./bid_settings/trie_dict.b"):
        """ 读取二进制文件中的dict变量, 赋给self.child
        Args:
            file_byte (str): 要读取的二进制文件
        """
        if file_read.split()[-1] == ".":
            with open(file_read, "rb") as f_r:
                self.child = pickle.load(f_r)
        else:
            with open(file_read, "r", encoding="utf-8") as f_r:
                f_read = f_r.read()
                self.child = json.loads(f_read)
        logger.info(f"init from file: {file_read}")

    def save_local(self, file_save="./bid_settings/title_trie.json"):
        folder = os.path.dirname(file_save)
        if not os.path.exists(folder):
            os.mkdir(folder)
        if file_save.split()[-1] == "b":
            with open(file_save, "wb") as f_w:
                pickle.dump(self.child, f_w)
        else:
            save_json(self.child, file_save)
        logger.info(f"save byte file: {file_save}")

    def insert_from_file(self, trie_file):
        """ 从文本文件中遍历每行,插入前缀树
        Args:
            trie_file (str): 前缀树文件路径
        """
        
        with open(trie_file, "r", encoding="utf-8") as f_r:
            for line in f_r:
                self.insert_from_str(line.strip())
        logger.info(f"init from file: {trie_file}")

    def _insert(self, word: str, root=True, child_p=-1) -> int:
        """ 将字符串插入前缀树
        Args:
            word (str): 要插入的字符串
            child_p (int): child节点的内存地址,需要使用id()获得
        Returns:
            id(c) (int): 最后插入的字符所在的内存地址
        """
        warning_list = []  # 储存不符合规范的字符,用于打印
        if root:
            c = self.child
        else:
            if child_p < 1:
                logger.error(f"input memory address: {child_p}, words: {word}")
            else:
                c = _get_p(child_p)
        for wd in word:
            if wd in c:
                c = c[wd]
            else:
                if wd in ("", " ", "："):  #TODO 错误检查,检查是否有符号,符号是否符合要求
                    warning_list.append(wd)
                else:
                    c[wd] = {}
                    c = c[wd]
        if warning_list:
            logger.warning(f"insert word: {word} has {warning_list}")
        c["end"] = True
        return id(c)

    def search(self, word: str) -> bool:
        """ 查找字符串是否在前缀树中 , 需要被查找的字符的节点有 "end"
        Args:
            word (str): 要查找的字符串
        Returns:
            (bool): 找到返回True , 找不到返回 False
        """
        c = self.child
        for wd in word:
            if wd in c:
                c = c[wd]
            else:
                return False
        if "end" in c:  # 有 end 则表示该节点为终止节点
            return True  # return word
        else:
            return False

    def startsWith(self, prefix: str) -> bool:
        """ 该字符串是否存在于前缀树中,不考虑 "end" 位
        Args:
            prefix:
        Returns:
            (bool) : 找到返回True 找不到返回False
        """
        c = self.child
        for wd in prefix:
            if wd in c:
                c = c[wd]
            else:
                return False
        return True

    def search_all(self, text):
        """
        Args:
            text:

        Returns:
            word_match (list): 返回符合规则的关键词,当有第二关键词时 len > 2
        """
        word_match = []
        c_next = None
        c = self.child
        first = second = False  # 第一关键词是否匹配, 匹配到第一关键词为True
        slow = 0  # 快指针
        for fast, wd in enumerate(text):
            wd = wd.upper()  # 小写转大写,仅影响英文字母
            if wd in c:  # 进入前缀树匹配
                c = c[wd]
                first = True
                # 匹配到带"end"的字,树中有从slow到fast的词, 从第一关键词换到第二关键词匹配
                if "end" in c:
                    second = True
                    word_match.append(text[slow: fast + 1])
                    c_next = c
            else:
                if second:
                    c = c_next
                elif first:
                    c = self.child  # 若第一关键词未匹配则回到上次节点
                slow = fast + 1
        return word_match

init_file = "./bid_settings/title_trie.json"

try:
    title_trie = BidTitleTrie(init_file)
except FileNotFoundError as e:
    logger.warning(f"{e}")
    title_trie = BidTitleTrie()

if __name__ == "__main__":
    title_trie.insert_from_file("./test/前缀树.txt")
    title_trie.save_local(init_file)
    # logger.info(title_trie.search_all("食堂led大宗食品面饼屏采购项目（二次）-招标公告"))
