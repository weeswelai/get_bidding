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

    def get_next_pages_url(self, list_url="", next_rule=None, **kwargs) -> str:
        next_rule = next_rule if next_rule else self.next_rule
        if isinstance(next_rule, str):
            next_rule = re.compile(next_rule)
        list_url = list_url if list_url else self.list_url
        if "index.jhtml" in list_url:
            next_pages_url = list_url.replace("index.jhtml", "index_2.jhtml")
        else:
            pages = str(int(next_rule.search(list_url).group()) + 1)
            next_pages_url = next_rule.sub(pages, list_url)
        self.get_list.config.update_referer(list_url)
        logger.info("get next pages url")
        return next_pages_url

    def get_pages(self):
        if "index.jhtml" in self.list_url:
            return "1"
        else:
            return self.next_rule.search(self.list_url).group()


if __name__ == "__main__":
    # test code
    pass
