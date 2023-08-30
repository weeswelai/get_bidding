"""
 本模块的功能为
 对于一个招标网站的 招标项目列表 的 页面 有如下操作
 1. 解析页面, 裁剪页面
 2. 用bs4解析html源码
 3. 解析招标项目所在的tag
 4. 获得招标信息

"""
from bs4 import BeautifulSoup as btfs
from bs4 import Tag

from module.config import config
from module.log import logger
from module.utils import *


PATH_RULE = 0
INDEX_RULE = 1
ATTR_RULE = 2


def tag_deep_get(tag: Tag, rule, *argv) -> Tag or None:
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
    return tag_deep_get(tag.find(rule[0]), rule[1:])


def tag_find(tag: Tag, name, index=0, attr={}, *argv):
    # rule: "tag1 > attr1"
    if not name:
        return tag
    if isinstance(index, int):
        return tag.find_all(name, limit=index+1, attrs=attr)[index]
    else:
        """ rule: "tag1,ALL,attr=value" """
        return tag.find_all(name, attrs=attr)


def get_tag_list_content(tag_list, attr_name=None):
    """ rule: "tag1,ALL,attr=value" """
    text = ""
    for t in tag_list:
        text += f"{get_tag_content(t, attr_name)}"
    return text


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


class TagRule:
    tag_rule = None
    attr_rule = None

    def __init__(self, name, rule) -> None:
        self.tag_fun = tag_find
        self.attr_fun = get_tag_content
        self.name = name
        self.rule = rule
        self.init_rule(rule)
        logger.info(f"tag: {self.tag_rule} {self.tag_fun.__name__} ,"
            f"attr: {self.attr_rule} {self.attr_fun.__name__}")

    def init_rule(self, rule):
        """
        Args:
            rule (str): 
        """
        # 预处理分割rule
        logger.info(f"{self.name}: {rule}")

        if not rule:
            self.get = return_none
            return

        if ">" in rule:
            _rule, attr_rule = rule.split(">")
            self.attr_rule = attr_rule.strip()
        else:
            _rule = rule

        if "." in _rule:
            self.tag_fun = tag_deep_get
            self.tag_rule[PATH_RULE] = _rule
            return
        self.set_tag_rule(*_rule.split(","))

    def set_tag_rule(self, tag_name, index=0, attr=""):
        self.tag_rule = ["", 0, {}]
        if tag_name:
            self.tag_rule[PATH_RULE] = tag_name.strip()
        if isinstance(index, str):
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
        target: Tag = self.tag_fun(tag, *self.tag_rule)
        return self.attr_fun(target, self.attr_rule)


# 仅对li_tag中的元素(可能为Tag或dict)进行处理
class BidTag:
    infoList: list = None
    type_r: TagRule
    url_r: TagRule
    date_r: TagRule
    name_r: TagRule
    tag: Tag
    rule_now = None

    def __init__(self, rules: dict = None, tag_rule: TagRule = TagRule):
        logger.hr("BidTag.__init__", 3)
        rules = rules or config.get_task("BidTag")
        for r, value in rules.items():
            setattr(self, r, tag_rule(r, value))

    def get_info(self, bid_tag: Tag or dict) -> list:
        """ 用规则获得一个tag或dict中对应的数据
         return [name, date, url, b_type]
        Args:
            bid_tag (Tag or dict): 招标项目对象
        """
        self.tag = bid_tag
        self.infoList = []
        for key in ("name_r", "date_r", "url_r", "type_r"):
            self.rule_now = key
            r: TagRule = getattr(self, key)
            data = r.get(self.tag)
            self.infoList.append(data)
        return self.infoList


class Bid:
    # 解析后的bid信息
    # Bid: 用于 module.web 中的继承，保存一个网页列表中招标项目的最终信息
    type: str
    url: str
    date: str
    name: str
    name_cut: re.Pattern = None
    date_cut: re.Pattern = None
    type_cut: re.Pattern = None
    url_cut: re.Pattern = None
    url_root: str
    infoList: list = None
    rule_now: str

    def __init__(self, settings=None):
        """ 定义项目对象,

        Args:
            settings (dict): 需要一整个task的设置
        """
        logger.hr("Bid.__init__", 3)
        settings = settings if settings else config.get_task()
        rule = settings["Bid"]["re"]
        for k, v in rule.items():
            setattr(self, k, init_re(v))
            logger.debug(f"rule init {k}: {getattr(self, k)}")
        self.url_root = settings["Bid"]["urlRoot"]

    def receive(self, *args):
        """ 接收BidTag.get()返回的list
        Args:
            *args: (name, date, url, type)
        """
        for idx, key in enumerate(("name", "date", "url", "type")):
            self.rule_now = key
            rule = getattr(self, f"{key}_cut")
            fun = getattr(self, f"{key}_get")
            data = _re_get_str(args[idx], rule)
            data_set = fun(data)
            self._set(key, data_set)

        self.infoList = [self.name, self.date, self.url, self.type]

    def url_get(self, url):
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

    def name_get(self, name):
        return name

    def type_get(self, type):
        if type in ["", " ", None]:
            return "None"
        return type

    def date_get(self, date):
        return date.replace("年", "-").replace("月", "-").replace("日", "")

    def _set(self, key, data:str):
        if "\n" in data:
            data = data.replace("\n", "")
        setattr(self, key, data)

    def message(self) -> str:
        # infoList 的最后一位可能是 None
        return f"{'; '.join(self.infoList[:-1])}; {str(self.infoList[-1])}"


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
    if isinstance(cut_rule, str):
        return re.search(cut_rule, obj).group()
    if rule is None or rule.pattern == "":
        return obj
    return rule.search(obj).group()


class ListBrows:
    """
    项目列表页面对象
    """
    html_cut = ""  # cut_html 后保存
    bs: Tag or dict = None
    li_tag = None
    tag_list = None

    def __init__(self, settings=None):
        settings = settings if settings else config.get_task()
        self.li_tag: str = settings["brows"]["li_tag"]

    def get_tag_list(self, page=None, li_tag=None, parse="html.parser"):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据bs_tag提取list
        Args:
            li_tag:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            parse (str): 解析html的bs4模式 默认为 html.parser
            t ()
        Returns:
            bid_list (list): 提取到的list
        """
        logger.info("web_brows.Html.get_tag_list")
        if not li_tag:  # 仅测试中使用
            li_tag = self.li_tag
        if isinstance(page, str):
            self.html_cut = page
            logger.info(f"get tag list from \"{page.strip()[: 100]}\"")
        # TODO 捕获错误判断
        self.bs = btfs(self.html_cut, features=parse)  # bs解析结果
        self.tag_list = self.bs.find_all(li_tag)
        return self.tag_list


# class BidHtml(ReqOpen):
#     def __init__(self, settings):
#         pass


if __name__ == "__main__":

    config.name = "zgzf"
    tag = BidTag()
    bid = Bid()
    list_brows = ListBrows()
    with open("./html_test/zgzf_test.html", "r", encoding="utf-8") as f:
        tag_li = list_brows.get_tag_list(f.read())

    for t in tag_li:
        bid.receive(*tag.get_info(t))
        print(bid.infoList)
    pass
