"""
通用模板
"""

import module.web_brows as web_brows
from module.log import logger
from module.utils import *


class Bid(web_brows.BidBase):
    pass


class Brows(web_brows.DefaultWebBrows):
    pass

    def open_url(self, timeout=180):
        return super().open_url(timeout)
