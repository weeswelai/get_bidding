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


class Task(task.BidTask):
    def __init__(self, name) -> None:
        self.get_list = GetList()
        self.bid = BidBase()
        self.tag = BidTag()
        self.brows = ListBrows()
        super().__init__(name)


if __name__ == "__main__":
    # test code
    pass
