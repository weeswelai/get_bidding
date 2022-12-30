"""
url打开模块
打开网页, 保存html源码
"""

from ntpath import join
import urllib.error as urlerr
import urllib.request as urlreq
from urllib.parse import urlencode
from sys import exit

from module.log import logger
from module.utils import *

_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }


class UrlOpen:
    url_response: bytes = None  # 原始bytes数据 read后
    html_cut: str = None
    response: str = None  # read后的数据再decode, 默认为 utf-8解析
    req: urlreq.Request = None

    def __init__(self, headers=None, method="GET"):
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
        self.decode_response()

    def init_req(self, url="http://127.0.0.1", 
                 headers=None, method=None, form=None):
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
        if isinstance(url, dict):
            form = url["form"]
            url = url["url"]
        data = bytes(urlencode(form), encoding="utf-8") if form else None
        self.req = urlreq.Request(url=url, method=method, data=data)
        if headers:
            for head, value in headers.items():
                self.req.add_header(head, value)

    def open_url(self, req=None, timeout=10):
        """ 打开self.REQ的网页,保存源码(bytes)
        
        """
        if not req:
            req = self.req
        logger.info(f"open {req.full_url}\n"
                    f"method:{req.method}, data:{req.data}")
        self.url_response = None
        open_error = None
        try:
            self.url_response = urlreq.urlopen(req, timeout=timeout).read()
        # TODO 超时的异常捕获
        except (urlerr.HTTPError, urlerr.URLError) as url_error:
            logger.error(
                f"open {req.full_url} Failed HTTPError: {url_error}\n"
                f"HTTP Status Code: {url_error.code}\n"
                f"req: url: {req.full_url}\nheaders: {jsdump(req.headers)}\n"
                f"method: {req.method}, data:{req.data}")         
            open_error = url_error
            # exit(1)  # 未来可能不终止
        assert open_error is None, open_error  # raise 给上级抛出异常
        return self.url_response

    def decode_response(self):
        """
        AttributeError: 'HTTPResponse' object has no attribute 'decode'
        可能会有AttributeError: 'NoneType' object has no attribute 'decode'
        """
        # self.url_response (str): 经过urlopen返回的response.read().decode()后的源码
        decoding = "utf-8"
        try:
            self.response = self.url_response.decode(decoding)
        except UnicodeDecodeError:
            decoding = "gbk"
            self.response = self.url_response.decode(decoding)
        except AttributeError:
            if self.url_response is None:
                logger.error("url_response is None")  # 当网站无返回时
            else:
                self.response = self.url_response  # 仅用于读取文件给url_response
        return self.response

    def save_response(self, rps="", url="", path="./html_save/",
                      save_date=False, extra=""):
        """保存response

        Args:
            rps (str): response,为空时使用self.url_response
            url (str): 网页url,为空时使用self.req.full_url
            path (str): html文件相对路径,默认为 ./html_save
            save_date (bool): 是带有保存带时间的新文件
            仅在浏览列表页面出错时或测试时保存使用
        """
        if not url:
            url = self.req.full_url
        if not rps:
            rps = self.response
        if path[-1] != "/":
            path = f"{path}/"
        file_name = path + url_to_filename(url)
        name_list = file_name.split(".")
        # 添加额外名称
        if self.method == "POST" and self.req.data:
            name_list[-2] = f"{name_list[-2]}_{self.req.data.decode('utf-8')}"
        elif self.method == "POST" and self.req.data is None:
            name_list[-2] = f"{name_list[-2]}_from={self.req.data}"
        if save_date:
            name_list[-2] = f"{name_list[-2]}{date_now_s(True)}"
        if extra:
            name_list[-2] = f"{name_list[-2]}_{extra}"
        file_name = ".".join(name_list)
        logger.info(f"save html as {file_name}")
        save_file(file_name, rps)
        return file_name

    def get_response_from_file(self, file, save="url_response"):
        """ 将文件读取的数据赋给self.url_response, 仅在测试中使用
        Args:
            file (str): file路径或html字符串
            save (str): url_response: 保存在 self.url_response中
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
        if save == "url_response":
            self.url_response = response
        elif save == "html_cut":
            self.html_cut = response


if __name__ == "__main__":
    url_open = {
        "url":"http://bid.aited.cn/front/ajax_getBidList.do",
        "form": {
            "classId": "151",
            "key": "-1",
            "page": "1"
        }
    }
    test_headers = {
        "User-Agent": "233",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    test_method = "get"
    url_obj = UrlOpen(method="POST")
    url_obj.init_req(url_open, headers=test_headers)
    url_obj.open_url()
    print(url_obj.decode_response())
    url_obj.save_response(save_date=True, path="./html_test/", extra="test")
    
