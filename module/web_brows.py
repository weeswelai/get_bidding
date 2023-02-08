"""
 本模块的功能为
 对于一个招标网站的 招标项目列表 的 页面 有如下操作
 1. 解析页面, 裁剪页面
 2. 用bs4解析html源码
 3. 解析招标项目所在的tag
 4. 获得招标信息

"""
import gzip
import json
import re
from time import time
from urllib.parse import urlencode  

from bs4 import BeautifulSoup as btfs
from bs4 import Tag

from module.get_url import SocketOpen, ReqOpen
from module.log import logger
from module.utils import *


# 仅对li_tag中的元素(可能为Tag或dict)进行处理
class BidTag:
    message: list = None
    type_r: tuple
    url_r: tuple
    date_r: tuple
    name_r: tuple
    tag: Tag
    rule_now: tuple = None

    def __init__(self, settings=None):
        # settings: 整个task 的settings
        logger.hr("BidTag.__init__", 3)
        if settings:
            rule: dict = settings["rule"]["bid_tag"]
            for li_r, value in rule.items():
                self._init_list_rule(li_r, value)

    # TODO 解析规则这部分有点*,记得重写一下
    def _init_list_rule(self, li_r, rule: str):
        """ 将rule以 | 和 : 分隔, 最终得到一个元组,详细说明参考web_brows_test.py
            解析rule, 设置属性值
        Args:
            li_r (str): rule.bid_tag的key, 一般为name_r, date_r, url_r等
            rule (str): rule.bid_tag key对应的value, 
        """
        # 预处理分割rule
        tag_find = tag_name = find_all_idx = value_name = value = None
        if rule is None or rule == "":
            return setattr(self, li_r, (None,))
        if rule.count("|") == 2:  # 2个|认为有 find_all_idx, 用于find_all的索引
            tag_gets_r, value_gets_r, find_all_idx = rule.split("|")
        elif rule.count("|") == 1:  # 必须有1个 |
            tag_gets_r, value_gets_r = rule.split("|")
        elif rule.count("|") == 0:
            return setattr(self, li_r, (rule,))
        if tag_gets_r:
            tag_find, tag_name = tag_gets_r.split(":")
        if value_gets_r:
            value_name, value = value_gets_r.split(":")
        setattr(
            self, li_r, (tag_find, tag_name, find_all_idx, value_name, value))

    def get(self, bid_tag: Tag or dict) -> list:
        """ 用规则获得一个tag或dict中对应的数据
         return [name, date, url, b_type]
        Args:
            bid_tag (Tag or dict): 招标项目对象
        """
        self.tag = bid_tag
        self.message = []
        self.message.append(self.parse_rule(bid_tag, *getattr(self, "name_r")))
        self.message.append(self.parse_rule(bid_tag, *getattr(self, "date_r")))
        self.message.append(self.parse_rule(bid_tag, *getattr(self, "url_r")))
        self.message.append(self.parse_rule(bid_tag, *getattr(self, "type_r")))
        # for key in ("name_r", "date_r", "url_r", "type_r"):
        return self.message

    # TODO 写的太*了，记得重写,包括下面的_parse_bs_rule
    def parse_rule(self, tag: Tag or dict, *args) -> Tag or None or str:
        """ 判断tag类型, 接收规则并解析
        
        """
        self.rule_now = args
        if isinstance(tag, Tag):
            return _parse_bs_rule(tag, *args)

        elif isinstance(tag, dict) or isinstance(tag, list):
            return _parse_json_rule(tag, *args)
        return None


def _parse_bs_rule(tag: Tag,
                   tag_find="", tag_name="", find_all_idx=None,
                   value_name="", value="") -> None or str:
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
            if "".join(tag.get("class")) == value.replace(" ", ""):
                return tag.text.strip()  # class=value 的 text值
            else:  # 若当前tag的class不符合则用find
                return tag.find(class_=value).text.strip()  # tag内容文本
        elif value_name == "_Text":  # 没有属性只有text的标签
            return tag.text.strip()  # tag内容文本
        else:
            return tag.get(value_name).strip()  # tag属性值
    else:  # 若不检索属性值则直接返回tag
        return tag


def _parse_json_rule(tag: list or dict,
                     key_find=None, list_idx=None, *kwargs):
    """ 根据规则获得dict 或 list中的值

    Args:
        tag (dict or list):
    Returns:
        str or None
    """
    if isinstance(tag, dict):
        return deep_get(tag, list_idx)
    elif isinstance(tag, list):
        return tag[list_idx]


class BidProject:
    @classmethod
    def init(cls, settings, class_name: str):
        if class_name in ("zzlh", "hkgy", "jdcg", "qjc", "zhzb", "test", ""):
            return cls.Bid(settings)
        else:  # zgzf
            return getattr(cls, class_name.title())(settings)

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
        rule_now: str

        def __init__(self, settings=None):
            """ 定义项目对象,

            Args:
                settings (dict): 需要一整个task的设置
            """
            logger.hr("Bid.__init__", 3)
            if settings:
                rule = settings["rule"]["bid"]
                for r in rule:
                    setattr(self, r, init_re(rule[r]))
                    logger.debug(f"rule init {r}: {getattr(self, r)}")
                self.url_root = deep_get(settings, "urlConfig.root")

        def receive(self, *args):
            """ 接收BidTag.get()返回的list
            Args:
                *args: (name, date, url, type)
            """
            for idx, key in enumerate(("name", "date", "url", "type")):
                self.rule_now = key
                rule = getattr(self, f"{key}_cut")
                setattr(self, key, _re_get_str(args[idx], rule))
            
            self._url()  # TODO 是否应该根据type进行选择?
            self._date()
            self._name()
            self._date()
            self.message = [self.name, self.date, self.url, self.type]

        def _url(self):
            """ 用 前缀加上后缀得到网址
            输入bid_root对 json中的 name.url_open.url_root 进行查表
            Args:
                bid_root (str): 前缀索引
                bid_tail (str): 后缀
            """
            if self.type in self.url_root:
                self.url = f"{self.url_root[self.type]}{self.url}"
            else:
                self.url = f"{self.url_root['default']}{self.url}"

        def _name(self):
            pass

        def _type(self):
            pass

        def _date(self):
            self.date = self.date.replace("年", "-").replace("月", "-").replace("日", "")

    class Zgzf(Bid):
        def _date(self):
            self.date = self.date.replace(".", "-")


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


class ListWeb:
    """
    项目列表页面对象
    """
    cut_rule: re.Pattern = None  # init_re
    html_cut = ""  # cut_html 后保存
    bs: Tag or dict = None
    tag_rule: str
    first_bid: list = None

    def _list_web_init(self, settings: dict = None):
        """ 实例化时会初始化cookie, cut_rule, next_rule

        Args:
            settings (dict): 需要settings中的rule
        """
        logger.hr(f"{type(self).__name__}._list_web_init", 3)
        if settings:
            # init rule
            self.cut_rule = init_re(deep_get(settings, "cut"))
            self.tag_rule = deep_get(settings, "tag_list")

    def cut_html(self, cut_rule: dict or str = None):
        """ 裁剪得到的html源码, 保存到 self.html_cut
        某些html含过多无用信息,使用bs解析会变得非常慢,
        如zzlh的招标列表页面源码有一万多行的无用信息(目录页码),
        需要删去部分无用信息
        Html对象使用 search方式获得group的值

        Args:
            cut_rule (dict, str): 仅在测试中使用,裁剪的规则
                当 cut_rule 为str 时使用re.S 额外参数: . 匹配换行符 \n
                为dict时如下所示 \n
                cut_rule = {
                    "re_rule": "正则表达式",
                    "rule_option": "re.compile额外参数, 默认为re.S, 
                        re.S无法保存在json中,所以使用re.S在python中的 int值,值为 16"
                }
        Returns:
            html_cut(str): 使用正则裁剪后的html源码,也有可能不裁剪
        """
        logger.info("web_brows.cut_html")
        if not cut_rule:
            html_cut = self.cut_rule.search(self.response).group()
        elif isinstance(cut_rule, dict):
            html_cut = re.search(cut_rule["re_rule"], self.response,
                                    cut_rule["rule_option"]).group()
        elif isinstance(cut_rule, str):
            html_cut = self.response if cut_rule == "" else \
                re.search(cut_rule, self.response, re.S).group()
        return html_cut

    def get_tag_list(self, page=None, tag_rule=None, parse="html.parser"):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据tag_list提取list
        Args:
            tag_rule:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            parse (str): 解析html的bs4模式 默认为 html.parser
        Returns:
            bid_list (list): 提取到的list
        """
        logger.info("web_brows.Html.get_tag_list")
        if not tag_rule:  # 仅测试中使用
            tag_rule = self.tag_rule
        if isinstance(page, str):
            self.html_cut = page
            logger.info(f"get tag list from \"{page.strip()[: 100]}\"")

        self.bs = btfs(self.html_cut, features=parse)  # bs解析结果
        return self.bs.find_all(tag_rule)

    def compare_last_first(self, message):
        """ 比较每页第一个项目信息是否与上一页第一个完全相等, 若相等返回True
        """
        if message == self.first_bid:
            return True
        self.first_bid = message
        return False


class DefaultWebBrows(ListWeb, ReqOpen):
    """继承于 ListWeb和UrlOpen"""
    def __init__(self, settings={}):
        if settings:
            self._list_web_init(settings["rule"])


class Qjc(DefaultWebBrows):
    def url_extra(self, url):
        """ 只在以complete状态开始的任务获取开始网址时调用一次
            在qjc的网址后面
        """
        if url[-13:].isdigit():  # 若url末尾有时间
            return url
        return f"{url}&_t={str(time()).replace('.', '')[:13]}"

    def cut_html(self, *args):
        """ 用json.loads将字符串转换为dict
        """
        logger.info("web_brows.Qjc.cut_html")
        self.html_cut = json.loads(self.response)
        return self.html_cut

    def get_tag_list(self, page=None, tag_rule=None, *args):
        """ 得到json中的列表
        """
        logger.info("web_brows.Qjc.get_tag_list")
        if not tag_rule:
            tag_rule = self.tag_rule
        if page:
            if isinstance(page, dict):
                self.html_cut = page
            elif isinstance(page, str):
                self.html_cut = loads(page)
        self.bs = self.html_cut
        return deep_get(self.bs, tag_rule)


class Zhzb(DefaultWebBrows):
    def get_next_pages(self, list_url: dict, next_rule=None, *args):
        """ 针对post方式发送表单的下一页获取
        """
        pages = list_url["form"]["page"]
        if isinstance(pages, int):
            list_url["form"]["page"] += 1
        elif isinstance(pages, str):
            list_url["form"]["page"] = int(pages) + 1
        logger.info(f"web_brows.Zhzb.get_next_pages: {list_url}")
        return list_url


class Zgzf(DefaultWebBrows):
    COOKIE_TIME_START_KEY = "Hm_lvt_9459d8c503dd3c37b526898ff5aacadd"
    COOKIE_TIME_KEY = "Hm_lpvt_9459d8c503dd3c37b526898ff5aacadd"

    def __init__(self, settings) -> None:
        self._list_web_init(settings)

    def url_extra(self, url):
        result = re.search("&start.*timeType=?\d", url)
        if result is None:
            # 加上今天日期和类型
            format = "%Y:%m:%d"
            data = {
                "start_time": date_days(format=format),
                "end_time": date_days(-6, format=format),
                "timeType": 2
            }
            idx = url.find("&displayZone=")  # 和正常访问的网址一样, 也保证Referer相同
            url = f"{url[:idx]}&{urlencode(data)}{url[idx:]}"  # 转换为url中的ASCII码
        else:
            result = result.group()
            time_type_re = re.compile("(?<=timeType=)\d")
            # 将时间改为指定日期
            if time_type_re.search(result) != "6":
                url = time_type_re.sub("6", url)
        return url

    def get_next_pages(self, list_url, next_rule=None, *args):
        url = super().get_next_pages(list_url, next_rule, *args)
        self.headers["Referer"] = list_url  # 更新Referer
        return url

    # def open(self, url):
    #     return super().open(url, headers=self.headers)    

    # def decode_response(self):
    #     try:
    #         self.response = gzip.decompress(self.res_body).decode("utf-8")
    #     except OSError as e:
    #         logger.warning(e)
    #     except Exception:
    #         self.response = self.res_body.decode("utf-8")

    def too_many_open(self):
        """判断ip是否被限制访问"""
        if self.response:
            bs = btfs(self.response, "html.parser")
            result = _parse_bs_rule(bs,"tag_find","div.p",None,"_Text")
            if result.find("您的访问过于频繁,请稍后再试") > 0 or \
                result.find("您的访问行为异常,请稍后再试") > 0:
                logger.warning(cookie_dict_to_str(self.cookie))
                logger.warning(self.req.headers)
                return True
        return False

    def set_cookie(self):
        if self.response:
            re_text = r'(?<=document.cookie = \").*?(?=;)'
            if re_text:
                cookie_find = re.findall(re_text, self.response)
                logger.debug(f"html cookie: {cookie_find}")
                for cookie_add in cookie_find:
                    key, value = cookie_add.split("=")
                    self.cookie[key] = value.replace("\"", "").replace("+","")

        if self.url_response_open:
            headers: list = self.url_response_open.getheaders()
            for key in headers:
                if key[0] == "Set-Cookie":
                    cookie = key[1].split(";")[0]
                    logger.debug(f"res set-cookie: {key[1]}")
                    self._set_cookie(cookie)
            time_now = str(time())[:10]
            if self.COOKIE_TIME_START_KEY not in self.cookie:
                self.cookie[self.COOKIE_TIME_START_KEY] = time_now
            self.cookie[self.COOKIE_TIME_KEY] = time_now
        if self.cookie:
            self.headers["cookie"] = cookie_dict_to_str(self.cookie)
            # logger.info(self.cookie)

    def _set_cookie(self, set_cookie: str):
        key, value = set_cookie.split("=")
        if key == "HOY_TR":
            logger.debug(f"{key}: {value}")
        if key in self.cookie and value == "deleted":
            del(self.cookie[key])
        else:
            self.cookie[key] = value



def web_brows_init(settings: dict = None, url_task="test") -> DefaultWebBrows:
    """ 根据输入的 url_task 返回初始化好的 web_brows对象

    Args:
        settings (dict): 初始化要用到的settings, 为整个task的dict
        url_task (str): task_name, json 里第一级的key, 一般为 zzlh, zhzb等
    Returns:
        web_brows.DefaultWebBrows 或其他继承 DefaultWebBrows 的对象
        对于zgzf : 返回 Zgzf对象: class Zgzf(ListWeb, SocketOpen)
    """
    if settings:
        # web_brows
        glob = globals()
        if url_task in settings:
            settings = settings[url_task]
        c = glob["DefaultWebBrows"] if url_task in \
            ("zzlh", "hkgy", "jdcg", "test", "") else glob[url_task.title()]
        web_brows: DefaultWebBrows = c(settings)

        # get_url
        headers = {}
        method = settings["urlConfig"]["method"] \
            if "method" in settings["urlConfig"] else "GET"
        for key, value in settings["headers"].items():
            if key == "User-Agent" and value:
                headers["User-Agent"] = value[0]
            elif key == "Cookie" and value:  # key == "Cookie" and value: True and [] = []
                headers["Cookie"] = value
                web_brows.cookie = cookie_str_to_dict(value)
            elif key not in ("User-Agent", "Cookie"):
                headers[key] = value
        web_brows._get_url_init(headers, method)
        web_brows.next_rule = init_re(deep_get(settings, "rule.next_pages"))
        return web_brows
    else:
        return DefaultWebBrows()

class BidHtml(ReqOpen):
    def __init__(self, settings):
        pass



if __name__ == "__main__":
    # 这里只是测试对象的单个功能,要测试对一个页面的功能需要用 ./test/web_brows_test.py
    json_file = "./bid_settings/bid_settings.json"
    json_settings = read_json(json_file)
    # html_file = r"./html_test/search.ccgp.gov.cn bxsearch searchtype=1&page_index=1&pinMu=0&bidType=1&kw=&start_time=2023%3A01%3A05&end_time=2022%3A12%3A30&timeType=3_2023_01_05-16_39_55_cut_Error.html"
    # url = ""
    task = "zgzf"
    zgzf = web_brows_init(json_settings, task)
    zgzf.open("http://127.0.0.1:19999/get")
    # zgzf.get_response_from_file(html_file)
    # zgzf.set_cookie()
    pass
