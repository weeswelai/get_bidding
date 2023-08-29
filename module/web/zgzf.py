import re
from time import time
from urllib.parse import urlencode

from bs4 import BeautifulSoup as btfs
from requests.utils import cookiejar_from_dict

from module.exception import *
from module.log import logger
from module.task import Task
from module.utils import *
from module.web_brows import tag_find


class Zgzf(Task):
    set_cookie_r = re.compile(r"(?<=\s).{0,10}?=deleted")
    html_cookie_r = re.compile(r"(?<=document.cookie = \").*?(?=;)")
    url_r = re.compile(r"&start.*timeType=?\d")
    time_type_r = re.compile(r"(?<=timeType=)\d")

    def cut_judge(self):
        if self.response:
            bs = btfs(self.response, "html.parser")
            tag = tag_find(bs, "p", 0)
            text = tag.text
            if text.find("您的访问过于频繁,请稍后再试") > 0 or \
                text.find("您的访问行为异常,请稍后再试") > 0:
                raise WebTooManyVisits

    # Task
    def close(self):
        for k in ("HMF_CI", "HOY_TR", "HBB_HC", "JSESSIONID", "HMY_JC"):
            if k in self.cookies:
                logger.debug(f"cookie delete {k}:{self.cookies[k]}")
                del(self.cookies[k])
        super().close()

    def get_date(self, date: str):
        return date.replace(".", "-")

    # def tag_filterate(self):
    #     if self.bid.type.split("|")[0] in \
    #         ("公开招标公告", "竞争性谈判公告", "邀请招标公告", "竞争性磋商公告"):
    #         # logger.debug(self.bid.name)
    #         return True

    # GetList
    def url_extra(self, url):
        result = self.url_r.search(url)
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
            # 将时间改为指定日期
            if self.time_type_r.search(result) != "6":
                url = self.time_type_r.sub("6", url)
        return url

    def set_cookies(self):
        """
        增加headers_deleted_cookie方法调用
        """
        self.update_cookies(self.s.cookies.get_dict())
        cookies_html: dict = self.get_cookies_from_html()
        self.headers_deleted_cookie()
        if cookies_html:
            self.update_cookies(cookies_html)
        self.s.cookies = cookiejar_from_dict(self.cookies)
        self.save_cookies()

    def get_cookies_from_html(self, **kwargs):
        """
        部分cookie保存在返回的html中,用正则进行搜索
        """
        if not self.response:
            return None
        cookies = {}
        cookie_find = self.html_cookie_r.findall(self.response, re.S)
        logger.debug(f"html cookie: {cookie_find}")
        for cookie_add in cookie_find:
            key, value = cookie_add.split("=")
            if key == "HOY_TR":
                value = self.cookies_HOY_TR(value)
            value = value.replace(',"+"', "")
            cookies[key] = value
        return cookies

    def cookies_HOY_TR(self, HOY_TR: str, otr_index=0):
        """
        根据sbu_hc.js得到的规则,该js尚未解析,仅根据规律修改HOY_TR
        在不打开F12调试时,修改的下标为0
        打开F12控制台时可能为3或4
        初始HOY_TR的格式为 "csr,cnv,otr"
        csr: 修改的值的 value
        otr: 要修改的用户行为值
        cnv: 16进制数字表 , key
        """
        csr, cnv, otr = HOY_TR.split(",")
        csr_i = int(cnv[otr_index], 16)  # 4 为 16进制数字序号
        otr = list(otr)
        otr[otr_index] = csr[csr_i]
        cookies = f"{csr},{cnv},{''.join(otr)},0"
        return cookies

    def set_cookie_time(self):
        """
        时间戳

        """
        time_now = str(time())[:10]
        self.cookies["Hm_lpvt_9459d8c503dd3c37b526898ff5aacadd"] = time_now
        self.s.cookies = cookiejar_from_dict(self.cookies)

    def headers_deleted_cookie(self):
        """
        删除self.r.headers里value为deleted的cookie,因为这个cookie无法被session和
        requests.Response 捕获到,所以用正则进行查找

        """
        deleted_cookie = None
        set_cookies = self.r.headers.get("set-cookie")
        if set_cookies:
            deleted_cookie = self.set_cookie_r.findall(set_cookies)
        if deleted_cookie:
            logger.debug(f"deleted cookie: {deleted_cookie}")
            for cookie in deleted_cookie:
                k, _ = cookie.split("=")
                del(self.cookies[k])


if __name__ == "__main__":
    # test
    self = Zgzf("zgzf")
    self.get_response_from_file("./html_test/zgzf_test.html")
    self.html_cut = self.cut_html()
    self.get_tag_list()
    for idx, tag in enumerate(self.tag_list):
        self._parse_tag(tag, idx)
        logger.info(self.message())
    
    pass