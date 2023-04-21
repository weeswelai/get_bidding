"""
通用模板
"""

import module.web_brows as web_brows
from module.log import logger
from module.utils import *


class Bid(web_brows.BidBase):
    pass


class Brows(web_brows.DefaultWebBrows):

    def _open_url(self, timeout=180):
        return super()._open_url(timeout)

    def url_extra(self, url, *argv, **kwargv):
        # 暂时不知道规律，先用1998年加上今日日期
        date = date_days(0, "day")[-5:]
        url = url.replace("?", f"?searchDate=1998-{date}&")
        return url
