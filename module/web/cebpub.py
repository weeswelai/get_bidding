
from module.log import logger
from module.task import Task
from module.utils import date_days


class Cebpub(Task):
    def url_extra_params(self, url, *argv, **kwargv):
        # 暂时不知道规律，先用1998年加上今日日期
        date = date_days(0, "day")[-5:]
        url = url.replace("?", f"?searchDate=1998-{date}&")
        return url

if __name__ == "__main__":
    self = Cebpub("cebpub")
    self.get_response_from_file("./html_test/cebpub_test.html")
    self.html_cut = self.cut_html()
    self.get_tag_list()
    for idx, tag in enumerate(self.tag_list):
        self._parse_tag(tag, idx)
        logger.info(self.message())
    # self.run()
    pass