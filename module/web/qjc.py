
from time import time
import re

import module.get_url as get_url
import module.task as task
import module.web_brows as web_brows
from module.exception import CutError
from module.log import logger
from module.utils import *


class Response(get_url.Response):
    def __init__(self):
        pass

    def cut_html(self, *argv):
        logger.info("qjc.res.cut_html")
        error = ""
        if not self.response:
            error = "response is \"\""
        try:
            loads(self.response)
        except Exception:
            error = "json loads error"
        if error:
            raise CutError  # exception is caught at GetList._cut()
        return self.response


class GetList(get_url.GetList):

    redirect_cut = re.compile(r"(?<=\|dynamicurl\|).*?(?=\|wzwsmethod\|)")

    def __init__(self):
        super().__init__()
        self.res = Response()

    def url_extra(self, url):
        """ 只在以complete状态开始的任务获取开始网址时调用一次
            在qjc的网址后面
        """
        if url[-13:].isdigit():  # 若url末尾有时间
            return url
        return f"{url}&_t={str(time()).replace('.', '')[:13]}"

    def open_extra(self, **kwargs):
        url_redirect = self.redirect_cut.search(self.res.response)
        if url_redirect:
            url = f"http://www.weain.mil.cn{url_redirect.group()}" \
                  f"?wzwscspd=MC4wLjAuMA=="
            self.open(url)


class Bid(web_brows.Bid):
    pass


class TagRule(web_brows.TagRule):

    def init_rule(self, rule: str = ""):
        self.tag_fun = deep_get
        self.tag_rule = rule

    def get(self, tag):
        return self.tag_fun(tag, self.tag_rule)


class BidTag(web_brows.BidTag):
    pass


class ListBrows(web_brows.ListBrows):

    def get_tag_list(self, page=None, ListTag=None, *args):
        """ 得到json中的列表
        """
        logger.info("Qjc.get_tag_list")
        if not ListTag:
            ListTag = self.ListTag
        page = page if page else self.html_cut
        if page:
            if isinstance(page, dict):
                self.html_cut = page
            elif isinstance(page, str):
                self.html_cut = loads(page)
        self.bs = self.html_cut
        self.tag_list = deep_get(self.bs, ListTag)
        return self.tag_list


class Task(task.Task):
    def __init__(self, name) -> None:
        self.get_list = GetList()
        self.bid = Bid()
        self.tag = BidTag(tag_rule=TagRule)
        self.brows = ListBrows()
        super().__init__(name)


if __name__ == "__main__":
    # test code
    self = Task("qjc")
    self.get_list.res.get_response_from_file("./html_test/qjc_test.html")
    self.brows.html_cut = self.get_list.res.cut_html()
    self.brows.get_tag_list()
    for i, t in enumerate(self.brows.tag_list):
        self._bid_receive_bid_tag(t, i)
        logger.info(self.bid.message())
    pass
