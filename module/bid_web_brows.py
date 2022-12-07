"""
 本模块的功能为
 对于一个招标网站的 招标项目列表 的 页面 有如下操作
 1. 解析当前页面，记录第一个招标项目的 标题、日期，交给任务调度做判断
    1.1 若第一个项目为新发布的项目，继续，若不为新项目，则回到任务调度进行下一任务
    1.2 这里需要记录一些关于第一个招标项目的信息，储存在json中
 2. 遍历列表中的标题，对于标题，招标类型符合条件的(调用判断模块)
    2.1 交给任务调度模块判断是否已经获取过，若已获取过则停止并返回任务调度进行下一任务
    若没获取过则继续
    (这里不确定是先交给任务调度判断是否已获取过还是先判断是否符合条件)
    2.2 记录符合条件的项目 的 url 、 标题 、 时间 储存到文件中(可能会用到数据库)
    2.3 打开符合条件的项目的页面 、 调用页面模块对项目页面进行读取，由于涉及到访问频率，
        此处可能要返回给任务调度，由任务调度来打开项目页
 3. 返回任务调度，任务调度执行翻到下一页(涉及访问频率)
 4. 由任务调度来循环 1~3
"""
import re
from bs4 import BeautifulSoup as btfs
from sys import getsizeof

from module.get_url import WebFromUrlOpen
from module.utils import *
from module.bid_log import logger
from module.bid_judge_content import title_trie

HEADER = {
    "User-Agent": r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


def get_bid_url(url_root, bid_root, bid_tail):
    """ 用 前缀加上后缀得到网址
    输入bid_root对 json中的 name.url_open.url_root 进行查表
    Args:
        bid_root (str): 前缀索引
        bid_tail (str): 后缀
    """
    if bid_root in url_root:
        return f"{url_root[bid_root]}{bid_tail}"
    else:
        return f"{url_root['root']}{bid_tail}"


class WebBrows(WebFromUrlOpen):
    cut_rule: re.Pattern = None  # init_re
    next_pages_rule: re.Pattern = None  # init_re
    list_rule = {}
    date_cut_rule: re.Pattern = None  # init_re
    html_list_match = ""
    # next_pages_rule = ""
    list_idx = 0
    bid_list = []
    url_root = {}
    cutHtml: bool


    def init(self, settings):
        # 若有cookie 需求(使用第一个cookie)
        cookie = deep_get(settings, "url_open_cookie")
        if cookie:
            self.update_req(cookie=cookie[0])
        self.url_root = deep_get(settings, "url_open.url_root")
        # 项目列表页面爬取规则
        self.init_rule(deep_get(settings, "brows_rule"))

    def get_list(self, page=None, list_rule: dict = None, parse="html.parser"):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据list_rule提取list
        Args:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            list_rule (dict): 解析的规则,仅在测试中使用
            parse (str): 解析html的bs4模式 默认为 html.parser
        Returns:
            bid_list (list): 提取到的list
        """
        self.bid_list = []  # 重置
        logger.hr("bid_web_brows.get_list", 3)
        if isinstance(page, str):
            self.bs = btfs(page, features=parse)  # 获得bs解析结果
        else:
            self.bs = btfs(self.html_list_match, features=parse)  # 获得bs解析结果

        logger.info(
            "get list from " +
            f"""{page if page in ['url_response', 'html_list_match'] else
            'html read'}""")
        if not list_rule:
            list_rule = self.list_rule

        li_r, name_r, date_r, url_r, type_r = list_rule.values()

        tag_list = self.parse_bs_rule(self.bs, li_r)
        for idx, li_tag in enumerate(tag_list):
            self.list_idx = idx
            b_type = self.parse_bs_rule(li_tag, type_r)  # 项目类型 货物 工程 服务
            url = get_bid_url(
                self.url_root, b_type, self.parse_bs_rule(li_tag, url_r))  # url
            date = self.re_get_date_str(
                self.parse_bs_rule(li_tag, date_r)
            )  # 正则过滤,取出数字部分
            name = self.parse_bs_rule(li_tag, name_r)  # 标题
            bid_prj = [name, date, url, b_type]  # 合并为list
            self.bid_list.append(bid_prj)  # 加入当前总表
            # logger.info(f"list {idx} complete")  # 调试日志
        logger.info(f"get bid list :\n{str_list(self.bid_list)[0]}")
        self.list_idx = self.bs_tag = None
        return self.bid_list

    def cut_html(self, _cut_rule: dict = None):
        """
        某些html含过多无用信息，使用bs解析会变得非常慢，
        如zzlh的招标列表页面源码有一万多行的无用信息(目录页码)，
        需要删去部分无用信息
        Returns:
            self.list_match (str): 匹配结果
        """
        self.cutHtml = False
        logger.info("bid_web_brows.cut_html")
        if isinstance(_cut_rule, dict):
            self.html_list_match = re.search(
                _cut_rule["re_rule"],
                self.url_response,
                _cut_rule["rule_option"]).group()
        else:
            self.html_list_match = \
                self.cut_rule.search(self.url_response).group()
        self.cutHtml = True
        # response_s = getsizeof(self.url_response)
        # match_s = getsizeof(self.html_list_match)
        # logger.info(f"size of response: {response_s},size of response_match: " +
        #             f"{match_s} Difference: {response_s-match_s}")

        return self.html_list_match

    def re_get_date_str(self, date_str, date_cut_rule=None):
        """
        处理带时间的字符串时间
        Args:
            date_str (str): 要裁剪的时间变量, 通常为 "发布时间: 2022-11-11"
            date_cut_rule (str): 裁剪规则,仅在测试时使用
        Returns:

        """
        # 默认正则参数 (4)(数字)+(_,-,年)+(2)(数字)+(_,-,月)+(2)(数字)+(日),日可忽略
        if isinstance(date_cut_rule, str):
            return re.search(date_cut_rule, date_str).group()
        if self.date_cut_rule.pattern == "":
            return date_str
        return self.date_cut_rule.search(date_str).group()

    def init_rule(self, rule):
        """
        初始化规则
        # TODO 正则表达式初始化并保存,而不是每次都重新初始化
        Args:
            rule (dict):
        Returns:
            bool: rule有值返回 True,无值返回 False
        """
        logger.info("bid_web_brows.init_rule")
        if rule:
            for r in rule:
                if r == "re":
                    for re_rule in rule["re"]:
                        setattr(self, re_rule, init_re(rule["re"][re_rule]))
                else:
                    setattr(self, r, rule[r])
        logger.info(f"rule: {dumps(rule, indent=2, ensure_ascii=False)}")

    def get_next_pages(self, page_url, next_pages_rule=None):
        """
        Args:
            page_url (str): 项目列表网址
            next_pages_rule (str): 项目列表网址下一页规则,仅在测试时使用
        """
        if not next_pages_rule:
            next_pages_rule = self.next_pages_rule
        page_idx = int(next_pages_rule.search(page_url).group())
        next_pages_url = next_pages_rule.sub(str(page_idx + 1), page_url)
        logger.info(f"bid_web_brows.get_next_pages: {next_pages_url}")
        return next_pages_url


class BidHtml(WebFromUrlOpen):
    pass


web_brows = WebBrows(headers=HEADER)
bid_web = BidHtml(headers=HEADER)
