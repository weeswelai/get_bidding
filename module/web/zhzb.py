
import module.web_brows as web_brows
from module.log import logger
from module.utils import *


class Bid(web_brows.BidBase):
    pass


class Brows(web_brows.DefaultWebBrows):
    def get_next_pages(self, list_url: dict, next_rule=None, *args):
        """ 针对post方式发送表单的下一页获取
        """
        pages = list_url["form"]["page"]
        if isinstance(pages, int):
            list_url["form"]["page"] += 1
        elif isinstance(pages, str):
            list_url["form"]["page"] = int(pages) + 1
        logger.info(f"web_brows.Zhzb.get_next_pages: {list_url}")
        return list_url
