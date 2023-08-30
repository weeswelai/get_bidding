
from module.task import Task
from module.log import logger


class Zhzb(Task):
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
    
    def get_name(self, name:str):
        return name.replace("\\\"", "")

if __name__ == "__main__":
    # test code
    self = Zhzb("zhzb")
    self.get_response_from_file("./html_test/zhzb_test.html")
    self.html_cut = self.cut_html()
    self.get_tag_list()
    for idx, tag in enumerate(self.tag_list):
        self._parse_tag(tag, idx)
        logger.info(self.message())
    pass
