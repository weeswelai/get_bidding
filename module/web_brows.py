"""
 本模块的功能为
 对于一个招标网站的 招标项目列表 的 页面 有如下操作
 1. 解析当前页面，记录第一个招标项目的 标题、日期，交给任务调度做判断
    1.1 若第一个项目为新发布的项目，继续，若不为新项目，则回到任务调度进行下一任务
    1.2 这里需要记录一些关于第一个招标项目的信息，储存在json中
 2. 遍历列表中的标题，对于标题，招标类型符合条件的(调用判断模块)
    2.1 交给任务调度模块判断是否已经获取过，若已获取过则停止并返回任务调度进行下一任务
    若没获取过则继续
    在 bid_web_brows 里调用bid_task 
    或 在 bid_task 里得到bid_web_brows 的返回值
    或 在 bid_task 里使用全局变量(全局对象)
    同时 对符合条件的
    (这里不确定是先交给任务调度判断是否已获取过还是先判断是否符合条件)
    2.2 记录符合条件的项目 的 url 、 标题 、 时间 储存到文件中(可能会用到数据库)
    2.3 打开符合条件的项目的页面 、 调用页面模块对项目页面进行读取，由于涉及到访问频率，
        此处可能要返回给任务调度，由任务调度来打开项目页
 3. 返回任务调度，任务调度执行翻到下一页(涉及访问频率)
 4. 由任务调度来循环 1~3
"""
import json
import re

from bs4 import BeautifulSoup as btfs
from bs4 import Tag

from module.log import logger
from module.get_url import UrlOpen
from module.utils import *


# 仅对li_tag进行操作
class BidTag:
    type_r: tuple 
    url_r: tuple 
    date_r: tuple 
    name_r: tuple 
    tag: Tag
    get_now: str = None

    def __init__(self, settings):
        rule = settings["rule"]["bid_tag"]
        for li_r in rule:
            self._init_list_rule(li_r, rule[li_r])

    def _init_list_rule(self, li_r, rule):
        """
        """
        # 预处理分割rule
        find_all_idx = value_name = value = None
        if rule is None or rule == "":
            setattr(self, li_r, (None,))
            return None
        if rule.count("|") == 2:  # 2个|认为有 find_all_idx, 用于find_all的索引
            tag_gets_r, value_gets_r, find_all_idx = rule.split("|")
        elif rule.count("|") == 1:  # 必须有1个 |
            tag_gets_r, value_gets_r = rule.split("|")
        if tag_gets_r:
            tag_find, tag_name = tag_gets_r.split(":")
        if value_gets_r:
            value_name, value = value_gets_r.split(":")
        setattr(
            self, li_r, (tag_find, tag_name, find_all_idx, value_name, value))

    def get(self, bid_tag: Tag) -> list:
        """ return [name, date, url, b_type]
        """
        self.tag = bid_tag
        message = []
        message.append(self.parse_rule(bid_tag, *getattr(self, "name_r")))
        message.append(self.parse_rule(bid_tag, *getattr(self, "date_r")))
        message.append(self.parse_rule(bid_tag, *getattr(self, "url_r")))
        message.append(self.parse_rule(bid_tag, *getattr(self, "type_r")))
        # for key in ("name_r", "date_r", "url_r", "type_r"):
        return message

    # TODO 写的太*了，记得重写
    def parse_rule(self, tag: Tag or dict, *args) -> Tag or None or str:
        self.get_now = args
        if isinstance(tag, Tag):
            return self._parse_bs_rule(tag, *args)
        
        elif isinstance(tag, dict):
            return deep_get(tag, list(args))
        return None
    
    def _parse_bs_rule(self, tag: Tag,
                      tag_find="", tag_name="", find_all_idx=None,
                      value_name="", value="") -> Tag or None or str:
        """
        解析规则,找到tag或tagList(bs4.element.ResultSet),或符合规则的属性值或tag中的文本
        Args:
            tag (bs4.element.Tag): 要检索的tag
        Returns:
            tag or text or None, 可能有三种返回
            None: not rule 为 True时返回None
            tag (bs4.element.Tag, bs4.element.ResultSet): find或find_all的检索结果
            text (str): tag的内容文本, 或tag中符合规则的属性的值
        """
        if not tag_find:  # 无rule返回None
            return None

        # 检索tag
        if tag_find == "tagName_all":
            if value_name and value:  # 若有value检索要求,则find_all加上参数attrs
                tag = tag.find_all(tag_name, attrs={value_name: value})
            # 无value要求,直接用find_all搜索
            # 使用find_all(tag_name, attrs={"":""}) 会返回None,所以这里额外调用语句
            else:
                tag = tag.find_all(tag_name)
            if find_all_idx:  # 若有find_all 的索引要求,则返回该索引对应的tag
                tag = tag[int(find_all_idx)]
        elif tag_find == "tagName_find":  # 使用tagName,find方式检索
            if tag_name:
                tag = bs_deep_get(tag, tag_name)  # 调用额外函数返回Tag
        # 检索属性值
        if value_name:  # value_name有值 则检索属性值
            if value_name == "class":
                if "".join(tag.get("class")) == value.replace(" ", ""):  # class=value 的 text值
                    return tag.text.strip()  # tag内容文本
                else:  # 若当前tag的class不符合则用find
                    return tag.find(class_=value).text.strip()  # tag内容文本
            elif value_name == "_Text":  # 没有属性只有text的标签
                return tag.text.strip()  # tag内容文本
            else:
                return tag.get(value_name)  # tag属性值
        else:  # 若不检索属性值则直接返回tag或
            return tag


class Bid:
    type: str
    url: str
    date: str
    name: str
    name_cut: re.Pattern = None
    date_cut: re.Pattern = None
    type_cut: re.Pattern = None
    url_cut: re.Pattern = None
    url_root: dict
    message: list = None
    get_now: str

    def __init__(self, settings):
        rule = settings["rule"]["bid"]
        for r in rule:
            setattr(self, r, init_re(rule[r]))
        self.url_root = deep_get(settings, "url.root")

    def receive(self, *args):
        for idx, key in enumerate(("name", "date", "url",  "type")):
            self.get_now = key
            rule = getattr(self, f"{key}_cut")
            setattr(self, key, self.re_get_str(args[idx], rule))
        self.get_bid_url(self.type, self.url)  # TODO 是否应该根据type进行选择?
        self.message = [self.name, self.date, self.url, self.type]

    def re_get_str(self, obj: str, rule: re.Pattern = None, cut_rule=None):
        """
        处理带时间的字符串时间
        Args:
            date_str (str): 要裁剪的时间变量, 通常为 "发布时间: 2022-11-11"
            date_cut_rule (str): 裁剪规则,仅在测试时使用
        Returns:

        """
        # 默认正则参数 (4)(数字)+(_,-,年)+(2)(数字)+(_,-,月)+(2)(数字)+(日),日可忽略
        if isinstance(cut_rule, str):
            return re.search(cut_rule, obj).group()
        if rule is None or rule.pattern == "":
            return obj
        return rule.search(obj).group()
    
    def get_bid_url(self, bid_root, bid_tail):
        """ 用 前缀加上后缀得到网址
        输入bid_root对 json中的 name.url_open.url_root 进行查表
        Args:
            bid_root (str): 前缀索引
            bid_tail (str): 后缀
        """
        if bid_root in self.url_root:
            self.url = f"{self.url_root[bid_root]}{bid_tail}"
        else:
            self.url = f"{self.url_root['default']}{bid_tail}"


class WebBrows(UrlOpen):
    cut_rule: re.Pattern = None  # init_re
    next_pages_rule: re.Pattern = None  # init_re
    html_list_match = ""  # cut_html 后保存
    bs: Tag or dict = None
    tag_rule: str

    def __init__(self, settings: dict = None):
        super().__init__()
        """ cookie, cut_rule, next_pages_rule 初始化
        """
        # 若有cookie 需求(使用第一个cookie)
        if settings:
            cookie = deep_get(settings, "url.cookie")
            user_agent = deep_get(settings, "url.User-Agent")
            if cookie:
                self.headers["cookie"] = cookie[0]
            if user_agent:
                self.headers["User-Agent"] = user_agent[0]
            # init rule
            self.cut_rule = init_re(deep_get(settings, "rule.cut"))
            self.next_pages_rule = init_re(deep_get(settings, "rule.next_pages"))
            self.tag_rule = deep_get(settings, "rule.tag_list")

    def get_bs_tag_list(self, page=None, tag_rule=None, parse="html.parser", json_read=False):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据list_rule提取list
        Args:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            list_rule (dict): 解析的规则,仅在测试中使用
            parse (str): 解析html的bs4模式 默认为 html.parser
        Returns:
            bid_list (list): 提取到的list
        """
        logger.info("bid_web_brows.get_bs_tag_list")
        if not tag_rule:  # 仅测试中使用
            tag_rule = self.tag_rule
        if isinstance(page, str):
            self.html_list_match = page
            logger.info(f"get tag list from \"{page[: 100]}\"")
        if json_read:
            self.bs = json.loads(self.html_list_match)
            return deep_get(self.bs, tag_rule)
        else:
            self.bs = btfs(self.html_list_match, features=parse)  # bs解析结果
            return self.bs.find_all(tag_rule)

    def cut_html(self, cut_rule: dict = None):
        """
        某些html含过多无用信息，使用bs解析会变得非常慢，
        如zzlh的招标列表页面源码有一万多行的无用信息(目录页码)，
        需要删去部分无用信息
        
        Args
            
        Returns:
            self.list_match (str): 匹配结果
        """
        logger.info("bid_web_brows.cut_html")
        if isinstance(cut_rule, dict):
            self.html_list_match = re.search(cut_rule["re_rule"],
                                             self.url_response,
                                             cut_rule["rule_option"]).group()
        elif isinstance(cut_rule, str):
            if cut_rule == "":
                self.html_list_match = self.url_response
            self.html_list_match = re.search(cut_rule, self.url_response, 
                                             re.S).group()
        else:
            self.html_list_match = \
                self.cut_rule.search(self.url_response).group()

    def get_next_pages(self, page_url, next_pages_rule=None):
        """
        Args:
            page_url (str): 项目列表网址
            next_pages_rule (str): 项目列表网址下一页规则,仅在测试时使用
        """
        if not next_pages_rule:
            next_pages_rule = self.next_pages_rule
        if isinstance(next_pages_rule, str):
            next_pages_rule = re.compile(next_pages_rule)
        page_idx = int(next_pages_rule.search(page_url).group())
        next_pages_url = next_pages_rule.sub(str(page_idx + 1), page_url)
        logger.info(f"bid_web_brows.get_next_pages: {next_pages_url}")
        return next_pages_url


class BidHtml(UrlOpen):
    def __init__(self, settings):
        pass