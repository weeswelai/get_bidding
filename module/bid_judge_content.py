"""
TODO
遍历得到的网页列表，判断每个名称是否符合要求
对招标项目网页的具体内容进行判断,截至时间、标书获取等
"""

import pickle

from module.bid_log import logger
from module.utils import *


class BidTitleTrie:
    def __init__(self, read_file_b=""):
        self.child: dict = {"first": {}, "second": {}}
        if read_file_b:
            self.init_from_file_b(read_file_b)

    def insert_from_list(self, l_in: list):
        """  将列表中的所有字符串插入前缀树, 每个列表的元素形式为 "first:second"
        Args:
            l_in (list): 要插入的字符串列表
        """

        for word_in in l_in:
            word_first, word_second = word_in.replace(" ", "").split(":")
            if word_first:
                self.insert(word_first, tree="first")
            if word_second:
                self.insert(word_second, tree="second")

    def insert_from_str(self, word_insert, split=""):
        """ 传入str, 使用分隔符将输入的多行字符串分隔成list, 再分别存入前缀树中
        需要保证list的每个元素为 "first:second" 形式
        Args:
            word_insert (str): 要插入的字符串
            split (str): 分隔符,默认为 "", 为 ""时不分割元素,将字符串变为单个元素的list
        """
        if split == "":
            word_list = [word_insert]
        else:
            word_list = word_insert.split(split)
        self.insert_from_list(word_list)

    def init_from_file_b(self, file_byte="./test/trie_dict.b"):
        """ 读取二进制文件中的dict变量, 赋给self.child
        Args:
            file_byte (str): 要读取的二进制文件
        """
        with open(file_byte, "rb") as f_r:
            self.child = pickle.load(f_r)

    def save_local(self, file_save="./test/trie_dict.b"):
        folder = os.path.dirname(file_save)
        if not os.path.exists(folder):
            os.mkdir(folder)
        with open(file_save, "wb") as f_w:
            pickle.dump(self.child, f_w)

    def insert_from_file(self, trie_file):
        with open(trie_file, "r", encoding="utf-8") as f_r:
            for line in f_r:
                self.insert_from_str(line.strip())

    def insert(self, word: str, tree="first", root="") -> None:
        """ 将字符串插入前缀树
        Args:
            word (str): 要插入的字符串
            tree (str): 要插入的树
            root (str): 插入second树时需要的根节点
        """
        c = self.child[tree]
        for wd in word:
            if wd in c:
                c = c[wd]
            else:
                c[wd] = {}
                c = c[wd]
                # if
        c["end"] = True

    # def insert_second(self, word, root):
    #     """
    #
    #     Args:
    #         word:
    #         root:
    #     """
    #     c = self.child["second"]

    def search(self, word: str, tree="first") -> bool:
        """ 查找字符串是否在前缀树中 , 需要被查找的字符的节点有 "end"
        Args:
            word (str): 要查找的字符串
            tree (str): 搜索的前缀树, first 为第一个, second为第二个
        Returns:
            (bool): 找到返回True , 找不到返回 False
        """
        c = self.child[tree].copy()
        for wd in word:
            if wd in c:
                c = c[wd]
            else:
                return False
        if "end" in c:  # 有 end 则表示该节点为终止节点
            return word  # return True
        else:
            return False

    def startsWith(self, prefix: str, tree="first") -> bool:
        """ 该字符串是否存在于前缀树中,不考虑 "end" 位
        Args:
            prefix:
            tree:
        Returns:
            (bool) : 找到返回True 找不到返回False
        """
        c = self.child[tree].copy()
        for wd in prefix:
            if wd in c:
                c = c[wd]
            else:
                return False
        return True

    def search_all(self, text):
        tree = "first"
        c = self.child[tree].copy()
        c_next = False
        fast = 0
        slow = 0
        first = ""
        second = ""
        for fast, wd in enumerate(text):
            if wd in c and "end" in c[wd]:
                c_next = True
                if not first:
                    first = text[slow: fast + 1]
                    tree = "second"
                    c = self.child[tree].copy()
                elif not second:
                    second = text[slow: fast + 1]
                    return [first, second]
            elif wd in c:
                c = c[wd]
                c_next = True
            else:
                if c_next:
                    c = self.child[tree].copy()
                    c_next = False
                slow = fast + 1
        if first:
            return [first, second]
        else:
            return None










