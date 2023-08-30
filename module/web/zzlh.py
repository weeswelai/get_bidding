
from module.task import Task
from module.log import logger
from module.utils import *


class Zzlh(Task):
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
        self.update_referer(list_url)
        logger.info("get next pages url")
        return next_pages_url

    def get_pages(self):
        if "index.jhtml" in self.list_url:
            return "1"
        else:
            return self.next_rule.search(self.list_url).group()


if __name__ == "__main__":
    # test code
    self = Zzlh("zhzb")
    self.get_response_from_file("./html_test/365_test.html")
    self.html_cut = self.cut_html()
    self.get_tag_list()
    for idx, tag in enumerate(self.tag_list):
        self._parse_tag(tag, idx)
        logger.info(self.message())
    pass
