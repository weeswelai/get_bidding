
import time
from urllib.parse import urlencode

from bs4 import BeautifulStoneSoup as btfs

import module.web_brows as web_brows
from module.log import logger
from module.utils import *
from module.web_brows import _parse_bs_rule


class Bid(web_brows.BidBase):
    def _date(self):
        self.date = self.date.replace(".", "-")


class Brows(web_brows.DefaultWebBrows):
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
