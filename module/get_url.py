"""
url打开模块
打开网页, 保存html源码
"""
import re
import traceback
from urllib.parse import urlencode

import requests
import requests.utils as requtils
from requests.exceptions import ReadTimeout
from bs4 import BeautifulSoup as btfs

from module.exception import *
from module.log import logger
from module.utils import *

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }
MAX_ERROR_OPEN = 3
MAX_ERROR_SAVE = 2
PACKET_CAPTURE_PROXIES = {"http": "127.0.0.1:8888", "https": "127.0.0.1:8888"}
NO_SYSTEM_PROXIES = {"http": None, "https": None}
# VERIFY = False # True: https 请求时验证 SSL 证书
packet_capture = False  # 抓包开关
system_proxies = False  # 是否系统代理
TIMEOUT = 16

class RequestBase:
    """
    Only GET and POST methods are supported
    """
    response: str = ""  # response
    encoding = "utf-8"
    system_proxies = False  # 是否系统代理(False时不经过梯子的代理)
    _response = requests.models.Response()
    _session = requests.Session()

    def __init__(self, method="GET", headers=HEADERS, timeout=TIMEOUT, proxies=None):
        method = method.upper()
        assert method in ("GET", "POST"), f"{method} isn't GET or POST"
        self._open = self._get if method == "GET" else self._post
        # needful headers and params
        self.params  = {
            "headers": headers or HEADERS,
            "timeout": timeout or TIMEOUT
        }
        # if packet_capture:
        #     self.params["proxies"] = PACKET_CAPTURE_PROXIES.copy()
        #     self.params["verify"] = VERIFY

        # 要么显示地指定 proxies , 要么不过系统代理, 使用 proxies=None 会使用系统当前代理
        self.params['proxies'] = proxies or NO_SYSTEM_PROXIES.copy()

    def open(self, url, data=None, **kwargs) -> str:
        """
        if method is GET, ignore data param, if is POST, need data param.
        """
        if not kwargs:
            kwargs = self.params
        self._open(url=url, data=data, **kwargs)
        self._response.encoding = self.encoding  # destination code base
        self.response = self._response.text
        return self.response

    def _open(self, url, **kwargs):
        """
        Reload in __init__, is _get or _post
        """
        pass

    def _get(self, url, **kwargs):
        self._response = self._session.get(url=url, **kwargs)

    def _post(self, url, data=None, **kwargs):
        if isinstance(url, dict) and not data:
            url, data = url.values()
        self._response = self._session.post(url=url, data=data, **kwargs)

    def update_param(self, params: dict, cover=True):
        for key, value in params.items():
            if key in self.params and cover:
                continue
            self.params[key] = value

    @property
    def cookies_session(self) -> dict:
        """
        Cookies not stored in response but in session
        """
        cookies: dict = self._session.cookies.get_dict()
        return cookies.copy()

    @cookies_session.setter
    def cookies_session(self, cookies:dict):
        self._session.cookies = requtils.cookiejar_from_dict(cookies)


class RequestHeaders:
    config: dict
    request: RequestBase

    @property
    def cookies(self) -> dict:
        """
        Cookies in json
        """
        return self.config["cookies"]

    @cookies.setter
    def cookies(self, cookies: dict):
        """
        Save cookies in json
        """
        for k, v in cookies.items():
            if v == "deleted":
                del(self.config["cookies"][k])
            else:
                self.config["cookies"][k] = v

    @property
    def _referer(self):
        return self.config["headers"]["Referer"]

    @_referer.setter
    def referer(self, referer: str):
        self.config["headers"]["Referer"] = referer
        self.request.params["headers"]["Referer"] = referer


class ListWebResponse:
    request: RequestBase
    bs = None
    html_cut: str = ""
    html_cut_rule: re.Pattern
    config: dict
    li_tag: str

    def __init__(self, config=None, html_cut_rule=None, file=""):
        if config:
            html_cut_rule = config["OpenConfig"]["html_cut"]
        if file:
            self.request = RequestBase()
            self.get_response_from_file(file)
        self.html_cut_rule = init_re(html_cut_rule)

    def cut_html(self, rule: dict or str or re.Pattern = None, response=""):
        """ 裁剪得到的html源码, 保存到 self.html_cut
        某些html含过多无用信息,使用bs解析会变得非常慢,
        如zzlh的招标列表页面源码有一万多行的无用信息(目录页码), 需要删去部分无用信息
        Html对象使用 search方式获得group的值

        Args:
            rule (dict, str): 仅在测试中使用,裁剪的规则
                当 html_cut 为str 时使用re.S 额外参数: . 匹配换行符 \n
                为dict时如下所示 \n
                html_cut = {
                    "re_rule": "正则表达式",
                    "rule_option": "re.compile额外参数, 默认为re.S, 
                    re.S无法保存在json中,所以使用re.S在python中的 int值,值为 16"
                }
        Returns:
            html_cut(str): 使用正则裁剪后的html源码,也有可能不裁剪
        """
        logger.info("ListWebResponse.cut_html")
        rule = rule or self.html_cut_rule
        response = response or self.request.response
        if isinstance(rule, re.Pattern):
            html_cut = rule.search(response)
        else:
            pattern = init_re(rule)
            html_cut = pattern.search(response)
        if not html_cut:
            self.cut_judge()
            raise CutError(f"len response {len(response)}, cut rule {rule}")
        self.html_cut = html_cut.group()

    def cut_judge(self):
        """
        得到了网页,但是第一步cut出错
        """
        pass

    def get_tag_list(self, page=None, li_tag=None, parse="html.parser"):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据bs_tag提取list
        Args:
            li_tag:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            parse (str): 解析html的bs4模式 默认为 html.parser
        Returns:
            bid_list (list): 提取到的list
        """
        logger.info("ListWebResponse.get_tag_list")
        li_tag = li_tag or self.li_tag
        page = page or self.html_cut
        # TODO 捕获错误判断
        self.bs = btfs(self.html_cut, features=parse)  # bs解析结果
        self.tag_list = self.bs.find_all(li_tag)
        logger.info(f"tag list len {len(self.tag_list)}")

    def save_response(self, rps="", url="test.html", extra="", save_date=True, 
                      path="./html_error/",):
        """
        保存response，仅在浏览列表页面出错时或测试时保存使用

        Args:
            rps (str): response,为空时使用self.url_response_byte
            url (str): 网页url,为空时使用 test.html
            path (str): html文件相对路径,默认为 ./html_error
            save_date (bool): 是带有保存带时间的新文件
            extra:
        Returns:
            file_name (str): 保存的文件名
        """
        if isinstance(url, dict):
            data = url["form"] if "form" in url else ""
            full_url = url["url"]
        else:
            full_url = url
        rps = rps or self.request.response
        path = f"{path}/" if path[-1] != "/" else path
        file_name = path + url_to_filename(full_url)
        name_list = file_name.split(".")
        # 添加额外名称
        if isinstance(url, dict) and data:
            name_list[-2] = f"{name_list[-2]}_{urlencode(data)}"
        elif isinstance(url, dict) and data is None:
            name_list[-2] = f"{name_list[-2]}_form={data}"
        if save_date:
            name_list[-2] = f"{name_list[-2]}{date_now_s(True)}"
        if extra:
            name_list[-2] = f"{name_list[-2]}_{extra}"

        file_name = ".".join(name_list)
        save_file(file_name, rps)
        logger.info(f"save html as {file_name}")

    def get_response_from_file(self, file, html_cut=False):
        """ 将文件读取的数据赋给self.url_response_byte, 仅在测试中使用
        Args:
            file (str): file路径或html字符串
        """
        logger.hr("get_url.get_response_from_file", 3)
        try:
            with open(file, "r", encoding="utf-8") as f:
                response = f.read()
            logger.info(f"read html from file: {file.strip()[:100]}...")
        except (FileNotFoundError, OSError):
            response = file
            logger.info(f"read html from str: {file.strip()[:100]}...")
        self.request.response = response
        if html_cut:
            self.html_cut = response


class GetList(RequestHeaders, ListWebResponse):
    """
    Need config key: OpenConfig
    """
    config: dict
    request: RequestBase = None
    list_url: str

    def __init__(self, config: dict):
        logger.info("GetList.__init__")

        self.config = config["OpenConfig"]
        logger.info(f"OpenConfig: {self.config}")

        cookies = deep_get(self.config, "cookies")
        self.config["cookies"] = cookie_str_to_dict(cookies)

        self.html_cut_rule = init_re(deep_get(self.config, "html_cut"))

        headers = deep_get(self.config, "headers")
        if not headers:
            logger.warning(f"OpenConfig headers is None, use deffault")
            headers = HEADERS
        if not deep_get(self.config, "headers"):
            logger.warning(f"OpenConfig User-Agent is None, use deffault")
            headers["User-Agent"] = HEADERS["User-Agent"]

        self.li_tag = self.config["li_tag"]

        self.request = RequestBase(method=self.config["method"],
                                   headers=headers, 
                                   timeout=deep_get(self.config, "time_out"),
                                   proxies=deep_get(self.config, "proxies"))

    def url_extra_params(self, url, **kwargs):
        """
        一些网址后面要加上时间戳等额外的参数
        """
        return url

    def open_extra(self, **kwargs):
        """部分网址打开后需要额外做一些判断
        如 qjc 打开重定向网址
        """
        pass

    def open_url_get_list(self, count=0, save_count=0):
        self.request.cookies_session = self.cookies  # reset cookies from json

        count += 1
        if count > MAX_ERROR_OPEN:
            raise TooManyErrorOpen
        logger.info(f"{count} open {self.list_url}")

        try:
            self.request.open(self.list_url)
            self.cookies = self.request.cookies_session  # set new cookies to json
            self.referer = self.list_url
            self.open_extra()
            self.cut_html()
            self.get_tag_list()
        except (CutError, ReadTimeout) as e:
            logger.error(f"Error: {self.list_url}\n{traceback.format_exc()}")
            if isinstance(e, CutError) and save_count < MAX_ERROR_SAVE:
                self.save_response(url=self.list_url, save_date=True, extra="cut_Error")
            sleep_random((2, 3))
            self.open_url_get_list(count, save_count + 1)


if __name__ == "__main__":
    # test1
    # request = RequestBase()
    # request.open("http://127.0.0.1:23333/get")  # httpbin

    # test2
    # config = {
    #     "OpenConfig": {
    #         "method": "GET",
    #         "headers": {
    #             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    #         },
    #         "cookies": {
    #         },
    #         "html_cut": {
    #             "re_rule": "(<ul class=\"searchList\">).*?(</ul>)",
    #             "rule_option": 16
    #         },
    #         "li_tag": "li"
    #     }
    # }
    # url = "http://www.365trade.com.cn/jggs/index.jhtml?typeId=103"
    # get_list = GetList(config)
    # print(get_list.get_url_tag_list(url))

    # TODO read config from files
    # test3
    # config_file = "./bid_settings/bid_settings_test.json"    
    pass
