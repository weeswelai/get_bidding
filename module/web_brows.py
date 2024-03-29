"""
 本模块的功能为
 对于一个招标网站的 招标项目列表 的 页面 有如下操作
 1. 解析页面, 裁剪页面
 2. 用bs4解析html源码
 3. 解析招标项目所在的tag
 4. 获得招标信息

"""
from bs4 import Tag

from module.log import logger
from module.utils import *

PATH_RULE = 0
INDEX_RULE = 1
ATTR_RULE = 2


class BidObj:
    _name = None
    _date = None
    _url = None
    def __init__(self, message) -> None:
        if isinstance(message, (list, tuple)):
            self._name, self._date, self._url = message
        elif isinstance(message, dict):
            pass


def tag_get(tag: Tag, rule, *args) -> Tag or None:
    """ rule: "tag1.tag2.tag3 > attr1"
    from https://stackoverflow.com/questions/25833613/safe-method-to-get-value-of-nested-dictionary
    Args:
        s_tag (bs4.element.Tag): 要检索的tag
        rule (str, list): 检索规则,用 "." 分开
    Returns:
        tag (bs4.element.Tag)
    """
    if isinstance(rule, str):
        rule = rule.split(".")
    assert type(rule) is list
    if tag is None:
        return None
    if not rule:
        return tag
    return tag_get(tag.find(rule[0]), rule[1:])


def tag_find(tag: Tag, name, index=None, attr={}, slice=None, *args):
    # rule: "tag1 > attr1"
    if not name:
        return tag
    if isinstance(index, int):
        return tag.find_all(name, limit=index+1, attrs=attr)[index]
    if isinstance(slice, (list, tuple)):
        tag_list = []
        list_find = tag.find_all(name, attrs=attr)
        length = len(list_find)
        for idx in slice:
            if idx < length:
                tag_list.append(list_find[idx])
        return tag_list
    else:
        """ rule: "tag1,ALL,attr=value" """
        return tag.find_all(name, attrs=attr)


def get_tag_list_content(tag_list, attr_name=None):
    """ rule: "tag1,ALL,attr=value" """
    text = ""
    for t in tag_list:
        text += f"{get_tag_content(t, attr_name)} "
    return text.strip()


def get_tag_content(tag: Tag, attr_name=None):
    """ rule: "tag1 > attr=value" """
    if not attr_name:
        """ rule: "tag1 >" """
        text = str(tag.text).strip()
        return text
    attr = str(tag.get(attr_name)).strip()
    return attr


def return_none(*args):
    return "None"


# 仅对li_tag中的元素(可能为Tag或dict)进行处理
class BidTag:
    class TagGet:
        """
        Can be overloaded
        """
        tag_rule = None
        attr_rule = None

        def __init__(self, name=None, rule=None):
            self.rule = rule
            self.tag_fun = tag_find
            self.attr_fun = get_tag_content
            logger.info(f"{name}: {self.rule}")
            self.init_rule(rule)
            logger.info(f"tag: {self.tag_rule} {self.tag_fun.__name__} ,"
                f"attr: {self.attr_rule} {self.attr_fun.__name__}")

        def init_rule(self, rule):
            """ 预处理分割rule
            Args:
                rule (str): 
            """
            if not rule:
                self.get = return_none
                return

            if ">" in rule:
                _rule, attr_rule = rule.split(">")
                self.attr_rule = attr_rule.strip()
            else:
                _rule = rule

            if "." in _rule:
                self.tag_fun = tag_get
                self.tag_rule[PATH_RULE] = _rule
                return
            self.set_tag_rule(*_rule.split(","))

        def set_tag_rule(self, tag_name, index=0, attr=""):
            self.tag_rule = ["", 0, {}]
            if tag_name:
                self.tag_rule[PATH_RULE] = tag_name.strip()
            if isinstance(index, str) and index.isdigit():
                if index.isdigit():
                    self.tag_rule[INDEX_RULE] = int(index)
                else:
                    index = index.strip() 
                    assert index.upper() == "ALL", "index not ALL or int"
                    self.tag_rule[INDEX_RULE] = index
                    self.attr_fun = get_tag_list_content
            if attr:
                r = attr.split("=")
                self.tag_rule[ATTR_RULE] = {r[0] : r[1]}

        def get(self, tag):
            tag: Tag = self.tag_fun(tag, *self.tag_rule)
            return self.attr_fun(tag, self.attr_rule)


    tag_info: list = None  # get info in tag
    tag: Tag
    tag_key_now = None

    def __init__(self, config: dict = None):
        logger.info("BidTag.__init__")
        self.tag_rules = config["BidTag"]
        self.tag_get = {}  # {name: TagGet(), ...}  get a tag
        for key in ("name", "date", "url", "type"):
            self.tag_get[key] = self.TagGet(key, self.tag_rules[key])

    def get_tag_info(self, tag: Tag or dict) -> list:
        """ 用规则获得一个tag或dict中对应的数据
        return [name, date, url, b_type]
        Args:
            bid_tag (Tag or dict): 招标项目对象
        """
        self.tag = tag
        self.tag_info = []
        for key in ("name", "date", "url", "type"):
            self.tag_now = key
            data = self.tag_get[key].get(tag)
            self.tag_info.append(data)
        return self.tag_info


class Bid:
    # 解析后的bid信息
    # Bid: 用于 module.web 中的继承，保存一个网页列表中招标项目的最终信息
    bid_info: dict = None
    url_root: str
    info_list: list = None
    get_bid_now: str

    def __init__(self, config: dict = None):
        config = config["Bid"]
        self.url_root = config["urlRoot"]
        logger.info(f"Bid __init__\nBid: {config}")
        self.bid_cut = {}
        for k, v in config["re"].items():
            self.bid_cut[k] = init_re(v)
            logger.debug(f"rule init {k}: {self.bid_cut[k]}")

    def get_bid_info(self, *args):
        """ 接收BidTag.get()返回的list
        Args:
            *args: [name, date, url, type]
        """
        self.bid_info = {}
        if args and  isinstance(args[0], Tag):
            args = self.get_tag_info(args[0])
        for idx, key in enumerate(("name", "date", "url", "type")):
            self.get_bid_now = key
            re = deep_get(self.bid_cut, key)
            data = _re_get_str(args[idx], re)
            fun = getattr(self, f"get_{key}")
            data: str = fun(data)
            self.bid_info[key] = data.replace("\n", "")

        self.info_list = [*self.bid_info.values()]
        return self.info_list

    def get_url(self, url):
        """ 用 前缀加上后缀得到网址
        输入bid_root对 json中的 name.url_open.url_root 进行查表
        Args:
            bid_root (str): 前缀索引
            bid_tail (str): 后缀
        """
        # if self.type in self.url_root:
        #     self.url = f"{self.url_root[self.type]}{self.url}"
        # else:
        return f"{self.url_root}{url}"

    def get_name(self, name):
        return name

    def get_type(self, type):
        if type in ["", " ", None]:
            return "None"
        return type

    def get_date(self, date:str):
        return date.replace("年", "-").replace("月", "-").replace("日", "")

    def message(self) -> str:
        # info_list 的最后一位可能是 None
        return f"{'; '.join(self.info_list[:-1])}; {str(self.info_list[-1])}"


def _re_get_str(obj: str, rule: re.Pattern = None, cut_rule=None):
    """ 正则获取字符串

    Args:
        obj: 被匹配的字符
        rule: 编译好的正则
        cut_rule: 正则表达式, 仅在测试中使用
    Returns:
        (str): 返回re.search搜索结果
    """
    # 默认正则参数 (4)(数字)+(_,-,年)+(2)(数字)+(_,-,月)+(2)(数字)+(日),日可忽略
    if rule is None or rule.pattern == "":
        return obj
    if isinstance(cut_rule, str):
        return re.search(cut_rule, obj).group()
    return rule.search(obj).group()


# class BidHtml(ReqOpen):
#     def __init__(self, settings):
#         pass


if __name__ == "__main__":
    # test
    # from module.get_url import ListWebResponse

    # html_cut_rule = {
    #     "re_rule": "(<ul class=\"searchList\">).*?(</ul>)",
    #     "rule_option": 16
    #   }
    # li_tag = "li"
    # html_file = "./html_test/365_test.html"
    # brows = ListWebResponse(file=html_file)
    # brows.cut_html(html_cut_rule)

    # bid_tag_rule = {
    #     "BidTag": {
    #         "name": "span > title",
    #         "date": "i",
    #         "url": "a > href",
    #         "type": "em"
    #     }
    # }
    # bid_tag = BidTag(bid_tag_rule)

    # bid_rule = {
    #     "Bid": {
    #         "urlRoot": "http://www.365trade.com.cn",
    #         "re": {
    #             "date": "\\d{4}([_\\-年])\\d{2}([_\\-月])\\d{2}(|日)"
    #         }
    #     }
    # }
    # bid = Bid(bid_rule)

    # tag_list = brows.get_tag_list(li_tag=li_tag)

    # for tag in tag_list:
    #     # test BidTag
    #     tag_info = bid_tag.get_tag_info(tag)
    #     logger.debug(tag_info)

    #     # test Bid
    #     bid_info = bid.get_bid_info(*tag_info)
    #     logger.debug(bid_info)
    pass
