"""
url打开模块
打开网页, 保存html源码
"""
import gzip
import socket
import urllib.error as urlerr
import urllib.request as urlreq
from http.client import HTTPResponse
from urllib.parse import urlencode

from module.log import logger
from module.utils import *

_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }


class UrlOpen:
    url_response_open: HTTPResponse = None
    url_response_byte: bytes = None  # 原始bytes数据 read后
    html_cut: str = None
    response: str = None  # read后的数据再decode, 默认为 utf-8解析
    req: urlreq.Request = None
    url: str or dict = None
    cookie = {}

    def __init__(self, headers=None, method=None):
        self.headers = _HEADERS if headers in (None, {}, "") else headers
        self.method = "GET" if method in (None, "") else method.upper()
        self.init_req()

    def open(self, url, headers=None, method=None):
        """
        
        Args:
            url (str,dict): GET方式输入str, POST方式输入dict,
                dict应包含 form 信息
            **kwargs (dict): headers信息, method方式
        """
        if isinstance(url, dict):
            self.init_req(**url, headers=headers, method=method)
        else:
            self.init_req(url, headers=headers, method=method)
        self.open_url()
        return self.decode_response()

    def init_req(self, url="http://127.0.0.1", 
                 headers: dict = None, method=None, form=None):
        """封装请求头,默认模式为GET
        Args:
            url (str,dict): 请求网址
            headers (dict):
            method (str): 请求模式,默认为GET
            form (dict): 要封装的数据
        saves:
            self.req: urlreq封装的请求头
        """
        if not headers:  # 若无输入则用自己的header
            headers = self.headers
        if not method:
            method = self.method
        method = method.upper()
        self.url = url
        if isinstance(url, dict):
            form = url["form"]
            url = url["url"]
        data = bytes(urlencode(form), encoding="utf-8") if form else None
        self.req = urlreq.Request(url=url, method=method, data=data, headers=headers)
        # if headers:
        #     for head, value in headers.items():
        #         self.req.add_header(head, value)

    def open_url(self, timeout=6):
        """ 打开self.REQ的网页,保存源码(bytes)
        
        """
        logger.info(f"open {self.req.full_url}\n"
                    f"method:{self.req.method}, data:{self.req.data}")
        self.url_response_byte = None
        try:
            self.url_response_open = urlreq.urlopen(self.req, timeout=timeout)
        except (urlerr.HTTPError, urlerr.URLError) as url_error:
            logger.error(
                f"open {self.req.full_url} Failed HTTPError: {url_error}\n"
                f"HTTP Status Code: {url_error.code}\n"
                f"req: url: {self.req.full_url}\nheaders: {jsdump(self.req.headers)}\n"
                f"method: {self.req.method}, data:{self.req.data}")         
            assert False, "open url error"
        except socket.timeout:
            assert False, "socket.timeout: time out"
            # exit(1)

        self.url_response_byte = self.url_response_open.read()
        # self.url_response_byte.info().get("Content-Encoding")

        return self.url_response_byte

    def decode_response(self):
        """
        AttributeError: 'HTTPResponse' object has no attribute 'decode'
        可能会有AttributeError: 'NoneType' object has no attribute 'decode'
        """
        # self.url_response_byte (str): 经过urlopen返回的response.read().decode()后的源码
        decoding = "utf-8"
        self.response = None
        try:
            self.response = self.url_response_byte.decode(decoding)
        except UnicodeDecodeError:
            decoding = "gbk"
            try:
                self.response = self.url_response_byte.decode(decoding)
            # 尝试用gzip解压缩
            except UnicodeDecodeError:
                self.url_response_byte = gzip.decompress(self.url_response_byte)
                self.decode_response()
        except AttributeError:
            if self.url_response_byte is None:
                logger.error("url_response_byte is None")  # 当网站无返回时
            else:
                self.response = self.url_response_byte  # 仅用于读取文件给url_response
        return self.response

    def save_response(self, rps="", url="", path="./html_error/",
                      save_date=False, extra=""):
        """保存response

        Args:
            rps (str): response,为空时使用self.url_response_byte
            url (str): 网页url,为空时使用self.req.full_url
            path (str): html文件相对路径,默认为 ./html_error
            save_date (bool): 是带有保存带时间的新文件
            仅在浏览列表页面出错时或测试时保存使用
        """
        url = self.url if not url else url
        if isinstance(url, dict):
            data = url["form"] if "from" in url else self.req.data
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
        logger.info(f"save html as {file_name}")
        save_file(file_name, rps)
        return file_name

    def get_response_from_file(self, file, save="response"):
        """ 将文件读取的数据赋给self.url_response_byte, 仅在测试中使用
        Args:
            file (str): file路径或html字符串
            save (str): url_response_byte: 保存在 self.url_response中
                        html_cut: 保存在 self.html_cut中
        Returns:
            (str):  file 是文件还是 字符串
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


if __name__ == "__main__":
    pass
    # #  POST
    # url_open = {
    #     "url":"https://httpbin.org/post",
    #     "form": {
    #         "classId": "151",
    #         "key": "-1",
    #         "page": "1"
    #     }
    # }
    # test_headers = {
    #     "User-Agent": "233",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    # }
    # url_obj = UrlOpen(method="POST")
    # url_obj.init_req(url_open, headers=test_headers)
    # url_obj.open_url()
    # print(url_obj.decode_response())
    # url_obj.save_response(save_date=True, path="./html_test/", extra="test")
    
    # # GET
    # url_open = "https://httpbin.org/get"
    # test_headers = {
    #     "User-Agent": "233",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    # }
    # url_obj = UrlOpen(method="GET")
    # url_obj.init_req(url_open, headers=test_headers)
    # url_obj.open_url()
    # print(url_obj.decode_response())
    # url_obj.save_response(save_date=True, path="./html_test/", extra="test")
