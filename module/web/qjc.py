
from time import time

import module.get_url as get_url
import module.task as task
import module.web_brows as web_brows
from module.log import logger
from module.utils import *


class GetList(get_url.GetList):
    def url_extra(self, url):
        """ 只在以complete状态开始的任务获取开始网址时调用一次
            在qjc的网址后面
        """
        if url[-13:].isdigit():  # 若url末尾有时间
            return url
        return f"{url}&_t={str(time()).replace('.', '')[:13]}"


class BidBase(web_brows.BidBase):
    pass


class BidTag(web_brows.BidTag):
    pass


class ListBrows(web_brows.ListBrows):

    def cut_html(self, *args):
        """ 用json.loads将字符串转换为dict
        """
        logger.info("web_brows.Qjc.cut_html")
        self.html_cut = json.loads(self.response)
        return self.html_cut

    def get_tag_list(self, page=None, tag_rule=None, *args):
        """ 得到json中的列表
        """
        logger.info("web_brows.Qjc.get_tag_list")
        if not tag_rule:
            tag_rule = self.tag_rule
        if page:
            if isinstance(page, dict):
                self.html_cut = page
            elif isinstance(page, str):
                self.html_cut = loads(page)
        self.bs = self.html_cut
        return deep_get(self.bs, tag_rule)


class Task(task.BidTask):
    get_list = GetList()
    bid = BidBase()
    tag = BidTag()
    brows = ListBrows()


if __name__ == "__main__":
    # test code
    pass
