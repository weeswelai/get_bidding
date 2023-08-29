"""
url打开模块
打开网页, 保存html源码
"""
import traceback
from urllib.parse import urlencode

import requests
import requests.utils as requtils
from bs4 import BeautifulSoup as btfs

from module.config import TaskConfig, config
from module.exception import *
from module.log import logger
from module.utils import *

HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }
MAX_ERROR_OPEN = 3
MAX_ERROR_SAVE = 2
PACKET_CAPTURE_PROXIES = {"http": "127.0.0.1:8888", "https": "127.0.0.1:8888"}
NO_SYSTEM_PROXIES = {"http": None, "https": None}
VERIFY = False
packet_capture = False  # 抓包开关
system_proxies = False  # 是否系统代理

class OpenConfig(TaskConfig):
    def params(self):
        kwargs = {
            "headers": self.headers,
            "timeout": self.time_out
        }
        if packet_capture:  # 是否抓包
            kwargs["proxies"] = PACKET_CAPTURE_PROXIES
            kwargs["verify"] = VERIFY
        if not system_proxies:  # 是否使用系统代理
            kwargs['proxies'] = NO_SYSTEM_PROXIES
            if "verify" in kwargs:
                del(kwargs["verify"])
        return kwargs

    def save_cookies(self):
        config.set_task("OpenConfig.cookies", self.cookies)
        config.save()

    def update_cookies(self, cookies: dict):
        for k, v in cookies.items():
            self._update_cookies(k, v)

    def _update_cookies(self, k, v: str):
        if v == "deleted":
            del(self.cookies[k])
        else:
            self.cookies[k] = v

    def update_referer(self, referer: str):
        self.headers["Referer"] = referer


class ListWebResponse(OpenConfig):
    response: str = None
    bs = None

    def cut_html(self, rule: dict or str = None):
        """ 裁剪得到的html源码, 保存到 self.html_cut
        某些html含过多无用信息,使用bs解析会变得非常慢,
        如zzlh的招标列表页面源码有一万多行的无用信息(目录页码),
        需要删去部分无用信息
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
        logger.info("get_list.res.cut_html")
        rule = rule if rule else self.html_cut_rule
        if isinstance(rule, dict):
            html_cut = re.search(rule["re_rule"],
                                 self.response,
                                 rule["rule_option"])
        elif isinstance(rule, str):
            html_cut = re.search(rule, self.response, re.S) if rule else \
                       self.response 
        else:
            html_cut = self.html_cut_rule.search(self.response)
        if not html_cut:
            logger.debug(f"len response {len(self.response)}")
            logger.debug(f"cut rule {self.html_cut_rule}")
            raise CutError
        return html_cut.group()

    def get_tag_list(self, page=None, list_tag_rule=None, parse="html.parser"):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据bs_tag提取list
        Args:
            list_tag_rule:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            parse (str): 解析html的bs4模式 默认为 html.parser
        Returns:
            bid_list (list): 提取到的list
        """
        logger.info("ListWebResponse.get_tag_list")
        if not list_tag_rule:  # 仅测试中使用
            list_tag_rule = self.list_tag_rule
        if isinstance(page, str):
            self.html_cut = page
            logger.info(f"get tag list from \"{page.strip()[: 100]}\"")
        # TODO 捕获错误判断
        self.bs = btfs(self.html_cut, features=parse)  # bs解析结果
        self.tag_list = self.bs.find_all(list_tag_rule)
        return self.tag_list

    def save_response(self, rps="", url="test.html", path="./html_error/",
                      save_date=False, extra=""):
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
            data = url["form"] if "from" in url else ""
            full_url = url["url"]
        else:
            full_url = url
        rps = self.response if not rps else rps
        path = f"{path}/" if path[-1] != "/" else path
        file_name = path + url_to_filename(full_url)
        name_list = file_name.split(".")
        # 添加额外名称
        if isinstance(url, dict) and data:
            name_list[-2] = f"{name_list[-2]}_{urlencode(data)}"
        elif isinstance(url, dict) and data is None:
            name_list[-2] = f"{name_list[-2]}_from={data}"
        if save_date:
            name_list[-2] = f"{name_list[-2]}{date_now_s(True)}"
        if extra:
            name_list[-2] = f"{name_list[-2]}_{extra}"
        file_name = ".".join(name_list)
        save_file(file_name, rps)
        logger.info(f"save html as {file_name}")
        return file_name

    def get_response_from_file(self, file, save="response"):
        """ 将文件读取的数据赋给self.url_response_byte, 仅在测试中使用
        Args:
            file (str): file路径或html字符串
            save (str): url_response_byte: 保存在 self.url_response中
                        html_cut: 保存在 self.html_cut中
        """
        logger.hr("get_url.get_response_from_file", 3)
        try:
            with open(file, "r", encoding="utf-8") as f:
                response = f.read()
            logger.info(f"read html from file: {file.strip()[:100]}...")
        except (FileNotFoundError, OSError):
            response = file
            logger.info(f"read html from str: {file.strip()[:100]}...")
        setattr(self, save, response)


# TODO 将 open url 相关的函数和参数分开作一个类?
class GetList(ListWebResponse):
    list_url = ""
    r: requests.models.Response = None
    s: requests.Session = None

    def url_extra(self, url, **kwargs):
        return url

    def open_extra(self, **kwargs):
        pass

    def set_cookie_time(self):
        self.s.cookies = requtils.cookiejar_from_dict(self.cookies)

    def cut_judge(self):
        """
        得到了网页,但是第一步cut出错
        """
        pass

    def open(self, url, open_times=0, save_error=0):
        if not self.s:
            self.s = requests.Session()
        self.response = ""
        self.set_cookie_time()
        open_times += 1
        if open_times > MAX_ERROR_OPEN:
            raise TooManyErrorOpen
        logger.info(f"{open_times} open {url}")
        self.list_url = url
        error = ""
        try:
            self._open()
            self.open_extra()
        except Exception:
            error = f"open error: {self.list_url}\n{traceback.format_exc()}"
        if not error:
            html_cut, error, save_error = self._cut(save_error)
        if error:
            logger.error(error)
            sleep_random(self.delay)
            html_cut = self.open(url, open_times, save_error)
        return html_cut

    def _cut(self, save_error):
        error = ""
        html_cut = ""
        try:
            html_cut = self.cut_html()
        except Exception:  # html AttributeError json 
            error = f"cut error: {self.list_url}\n{traceback.format_exc()}"
            if save_error < MAX_ERROR_SAVE:
                save_error += 1
                self.save_response(url=self.list_url,
                                       save_date=True, extra="cut_Error")
            self.cut_judge()
        return html_cut, error, save_error

    def _open(self, **kwargs):
        method = self.method.upper()
        if not kwargs:
            kwargs = self.params()
        if method == "GET":
            self.r = self.s.get(url=self.list_url, **kwargs)
        elif method == "POST":
            url, data = self.list_url.values()
            self.r = self.s.post(url=url, data=data, **kwargs)
        else:
            logger.warning(f"error method: {method}")
            # raise
        self.r.encoding = self.encoding
        self.response = self.r.text
        self.set_cookies()

    def set_cookies(self):
        self.update_cookies(self.s.cookies.get_dict())
        cookies_html: dict = self.get_cookies_from_html()
        if cookies_html:
            self.update_cookies(cookies_html)
        self.s.cookies = requtils.cookiejar_from_dict(self.cookies)
        self.save_cookies()

    def get_cookies_from_html(self):
        return None
