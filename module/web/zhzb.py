
import module.get_url as get_url
import module.task as task
import module.web_brows as web_brows
from module.log import logger


class GetList(get_url.GetList):
    pass


class Bid(web_brows.Bid):
    
    def name_get(self, name:str):
        return name.replace("\\\"", "")


class BidTag(web_brows.BidTag):
    pass


class ListBrows(web_brows.ListBrows):
    pass


class Task(task.Task):
    def __init__(self, name) -> None:
        self.get_list = GetList()
        self.bid = Bid()
        self.tag = BidTag()
        self.brows = ListBrows()
        super().__init__(name)

    def get_next_pages_url(self, **kwargs):
        """ 针对post方式发送表单的下一页获取
        """
        pages = self.list_url["form"]["page"]
        if isinstance(pages, int):
            self.list_url["form"]["page"] += 1
        elif isinstance(pages, str):
            self.list_url["form"]["page"] = int(pages) + 1
        logger.info(f"zhzb.get_next_pages: {self.list_url}")
        return self.list_url

    def get_pages(self):
        return self.list_url["form"]["page"]

if __name__ == "__main__":
    # test code
    self = Task("zhzb")
    self.get_list.res.get_response_from_file("./html_test/zhzb_test.html")
    self.brows.html_cut = self.get_list.res.cut_html()
    self.brows.get_tag_list()
    for i, t in enumerate(self.brows.tag_list):
        self._bid_receive_bid_tag(t, i)
        logger.info(self.bid.message())
    pass
