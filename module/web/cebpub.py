"""
通用模板
"""

import module.get_url as get_url
import module.task as task
import module.web_brows as web_brows
from module.log import logger
from module.utils import *


class GetList(get_url.GetList):
    def url_extra(self, url, *argv, **kwargv):
        # 暂时不知道规律，先用1998年加上今日日期
        date = date_days(0, "day")[-5:]
        url = url.replace("?", f"?searchDate=1998-{date}&")
        return url


class BidBase(web_brows.BidBase):
    pass


class BidTag(web_brows.BidTag):
    pass


class ListBrows(web_brows.ListBrows):
    pass


class Task(task.BidTask):
    get_list = GetList()
    bid = BidBase()
    tag = BidTag()
    brows = ListBrows()


if __name__ == "__main__":
    # test code
    pass