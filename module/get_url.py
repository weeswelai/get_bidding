"""
url打开模块
打开网页
"""

import re
import urllib.request as urlreq
import urllib.error as urlerr
from bs4.element import Tag
from sys import exit

from module.bid_log import logger
from module.utils import *


class UrlOpen:
    def __init__(self, headers) -> None:
        self.headers = headers
        self.url_response = ""
        self.REQ = None
        self.url = ""
        self.method = "GET"  # 会在每次读取完网页后重置为 GET

    def init_req(self, url, headers="", method=""):
        """封装请求头,默认模式为GET
        Args:
            url (str): 请求网址
            headers (dict):
            method (str): 请求模式,默认为GET
        saves:
            : urlreq封装的请求头
        """
        if not headers:  # 若无输入则用自己的header
            headers = self.headers
        if not method:
            method = self.method
        self.REQ = urlreq.Request(url=url, headers=headers, method=method)
        self.url = url

    def update_req(self, **kwargs):
        """ 可选 url , headers, method, cookie
        Args:
            **kwargs (dict): url , headers, method, cookie
        """
        log = ""
        for k in kwargs:  # 遍历列表
            if hasattr(self, k):
                setattr(self, k, kwargs[k])
                log = f"{log}update {k} to {kwargs[k]}:\n"  # 打印log
            else:
                logger.warning(f"{k} not in {self.__class__.__name__}")
        logger.info(f"get_url.update_req:\n{log.strip()}")

    def open_url_get_response(self):
        """ 打开self.REQ的网页,保存源码到内存中
        self.url_response (str): 经过urlopen返回的response.read().decode()后的源码
        """
        try:
            url_response: bytes = urlreq.urlopen(self.REQ).read()
        except urlerr.HTTPError as http_error:
            logger.error(
                f"open {self.REQ.full_url} failed HTTPError: {http_error}\n" +
                f"REQ: url: {self.url}\nheaders: {self.headers}\n" +
                f"method: {self.method}")
            exit(1)  # 未来可能不终止
        except urlerr.URLError as url_error:
            # REQ.full_url: open 的 url
            logger.error(
                f"open {self.REQ.full_url} failed: {url_error}\n" +
                f"REQ: url: {self.url}\nheaders: {self.headers}\n" +
                f"method: {self.method}")
            exit(1)  # 未来可能不终止
        decoding = "utf-8"
        try:
            self.url_response = url_response.decode(decoding)
        except UnicodeDecodeError:
            decoding = "gbk"
            self.url_response = url_response.decode(decoding)
        self.method = "GET"  # 重置访问方法为GET

    def save_response(self, rps="", url="", path="./html_save/",
                      save_date=False, extra=""):
        """保存response
        目前需要适配的网址:
        http://www.365trade.com.cn/zbgg/index_1.jhtml
        >  365trade.com.cn、zbgg、index_1.jhtml

        Args:
            rps (str): response,为空时使用self.url_response
            url (str): 网页url,为空时使用self.url
            path (str): html文件相对路径,默认为 ./html_save
            save_date (bool): 是带有保存带时间的新文件
            仅在浏览列表页面出错时或测试时保存使用
        """
        if not url:
            url = self.url
        if not rps:
            rps = self.url_response
        file_name = path + url_to_filename(url)
        if save_date:
            point_idx = file_name.rindex('.')
            file_name = f"{file_name[: point_idx]}_{date_now_s(True)}" + \
                        f"{file_name[point_idx:]}"
        if extra:
            point_idx = file_name.rindex('.')
            file_name = f"{file_name[: point_idx]}_{extra}" + \
                        f"{file_name[point_idx:]}"
        logger.info(f"save html as {file_name}")
        save_file(file_name, rps)

    def get_response_from_file(self, file):
        """ 将文件读取的数据赋给self.url_response
        Args:
            file (str): file路径或html字符串
        Returns:
            (str):  file 是文件还是 字符串
        """
        logger.hr("get_url.get_response_from_file", 3)
        try:
            with open(file, "r", encoding="utf-8") as f:
                self.url_response = f.read()
            logger.info(f"read html from file: {file}")
            return "file"
        except (FileNotFoundError, OSError):
            self.url_response = file
            logger.info(f"read html from str: {file[:100]}...")
            return "html_read"
            