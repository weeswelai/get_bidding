
import re
from json.decoder import JSONDecodeError
from time import time

from module.exception import CutError
from module.log import logger
from module.task import Task
from module.utils import *


class Qjc(Task):
    redirect_cut = re.compile(r"(?<=\|dynamicurl\|).*?(?=\|wzwsmethod\|)")

    class TagGet(Task.TagGet):
        def init_rule(self, rule: str = ""):
            self.tag_fun = deep_get
            self.tag_rule = rule

        def get(self, tag):
            return self.tag_fun(tag, self.tag_rule)


    def get_tag_list(self, response=None, li_tag=None, *args):
        """ 得到json中的列表
        """
        logger.info("Qjc.get_tag_list")
        if not li_tag:
            li_tag = self.li_tag
        response = response or self.html_cut
        if not response:
            raise CutError("Response is ''")
        if isinstance(response, dict):
            self.html_cut = response
        elif isinstance(response, str):
            try:
                self.html_cut = json.loads(response)
            except JSONDecodeError:
                self.save_response(url=self.list_url, save_date=True, extra="cut_Error")
        self.bs = self.html_cut
        self.tag_list = deep_get(self.bs, li_tag)
        return self.tag_list

    def open_extra(self, **kwargs):
        """
        处理qjc的重定向
        """
        logger.info("Qjc url redirect")
        url_redirect = self.redirect_cut.search(self.request.response)
        if url_redirect:
            url = f"http://www.weain.mil.cn{url_redirect.group()}" \
                  f"?wzwscspd=MC4wLjAuMA=="
            self.request.open(url)

    def url_extra_params(self, url, **kwargs):
        """ 只在以complete状态开始的任务获取开始网址时调用一次
            在qjc的网址后面
        """
        if url[-13:].isdigit():  # 若url末尾有时间
            return url
        return f"{url}&_t={str(time.time()).replace('.', '')[:13]}"


if __name__ == "__main__":
    # test code
    from module.config import CONFIG
    CONFIG.task = "qjc"
    self = Qjc("qjc", CONFIG.task)
    self.get_response_from_file("./html_test/qjc_test.html")
    self.cut_html()
    self.get_tag_list()
    for idx, tag in enumerate(self.tag_list):
        self._parse_tag(tag, idx)
        logger.info(self.message())
