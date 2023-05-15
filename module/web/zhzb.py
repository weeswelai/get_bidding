
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
    get_list = GetList()
    bid = BidBase()
    tag = BidTag()
    brows = ListBrows()

    def get_next_pages(self, **kwargs):
        """ 针对post方式发送表单的下一页获取
        """
        pages = self.list_url["form"]["page"]
        if isinstance(pages, int):
            self.list_url["form"]["page"] += 1
        elif isinstance(pages, str):
            self.list_url["form"]["page"] = int(pages) + 1
        logger.info(f"zhzb.get_next_pages: {self.list_url}")
        return self.list_url


if __name__ == "__main__":
    # test code
    pass
