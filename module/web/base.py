"""
通用模板
"""


import module.get_url as get_url
import module.task as task
import module.web_brows as web_brows
from module.log import logger
from module.utils import *


class GetList(get_url.GetList):
    pass


class BidBase(web_brows.BidBase):
    pass


class BidTag(web_brows.BidTag):
    pass


class ListBrows(web_brows.ListBrows):
    pass


class Task(task.Task):
    def __init__(self, name) -> None:
        self.get_list = GetList()
        self.bid = BidBase()
        self.tag = BidTag()
        self.brows = ListBrows()
        super().__init__(name)


if __name__ == "__main__":
    # test code
    from module.config import config
    config.name = "hkgy"
    self = Task("hkgy")
    # self.get_list.res.get_response_from_file("./html_test/hkgy_test.html")
    # self.brows.html_cut = self.get_list.res.cut_html()
    # self.brows.get_tag_list()
    # for i, t in enumerate(self.brows.tag_list):
    #     self._bid_receive_bid_tag(t, i)
    #     logger.info(self.bid.message())
    self.run(restart=True)
    pass
