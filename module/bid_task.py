from copy import deepcopy
from datetime import datetime, timedelta

from module.config import CONFIG
from module.utils import date_days, time_difference
from module.web_brows import *


class StopBid:
    date: datetime

    def __init__(self, bid: dict = None) -> None:
        self.name = bid["name"]
        self.date_str = bid["date"]
        self.url = bid["url"]
        self.date_init()

    def __str__(self) -> str:
        return (f"\"name\": \"{self.name}\",\n"
                f"\"date\": \"{str(self.date)}\",\n"
                f"\"url\": \"{self.url}\"")

    def date_init(self):
        """ 判断 stopBid 是否合法
        """
        end_day = 1
        date_6 = date_days(-6, "day")
        if not self.date_str:
            self.date_str = date_6
        if len(self.date_str) <= 10:
            self.date_str += " 00:00:00"
        if time_difference(self.date_str, date_days(), "day") < -6:
            end_day = 0
            logger.info(f"end_rule: {self.date_str} is beyond 6 days")
            self.date_str = date_6
        self.date = datetime.strptime(self.date_str, "%Y-%m-%d %H:%M:%S") - \
                    timedelta(days=end_day)

    def bid_is_end(self, bid_prj: dict):
        """ 判断当前项目是否符合结束条件
        Args:
            bid_prj (<class> Bid): 当前Bid对象, 保存项目信息
        """
        # 名称和Url都相同时停止
        if bid_prj["name"] == self.name \
                and bid_prj["url"] == self.url:
            return True
        # 超出时间限制时停止
        if self._date_is_end(bid_prj["date"]):
            return True
        return False

    def _date_is_end(self, date: str):
        """ 
        判断爬到的项目日期是否比end_date减一天还晚
        仅作为保证不会因为找不到相同项目而爬到死循环的措施
        """
        if len(date) > 10:
            date_format = "%Y-%m-%d %H:%M:%S"
        else:
            date_format = "%Y-%m-%d"
        date = datetime.strptime(date, date_format)
        return date < self.date


class BidTask:
    interrupt = False
    newest = False
    start = True
    first_bid: list = None

    def __init__(self, name) -> None:
        self.name = name
        settings = CONFIG.get_task(name)
        self.state = settings["state"]
        self.stop_bid = StopBid(settings["stopBid"])
        self.set_task("stopBid.date", self.stop_bid.date_str)
        self.interrupt_url = settings["interruptUrl"]
        self.interrupt_bid = settings["interruptBid"]
        self.get_state()
        logger.info(f"newestBid: {self.get_task('newestBid')}")
        logger.info(f"stopBid: {self.stop_bid}")

    def set_task(self, key, data):
        CONFIG.set_task(f"{self.name}.{key}", data)

    def get_task(self, key=""):
        return CONFIG.get_task(f"{self.name}.{key}")

    def get_state(self):
        if self.state in ["complete", ""]:
            self.state = "run"

        elif self.state in ["error", "interrupt"]:
            if self.interrupt_bid["name"] and self.interrupt_bid["date"] and \
                    self.interrupt_bid["url"]:
                self.state = "interrupt"
                self.start = False
                self.interrupt = True
        logger.info(f"newest: {self.newest}, "
                    f"interrupt: {self.interrupt}, "
                    f"start: {self.start}")

    def bid_is_start(self, bid_info: dict):
        """判断条件为: name, date, url 三个信息必须全部符合, 符合返回True 并
        将 self.state 置为 True, 若有一个不符合则返回 False .
        仅在 interrupt状态下执行

        注意: json中state.interrupt 信息为自动生成, 
        若手动填写请注意是否填写正确,否则可能导致一直跳过当前招标项目,
        直到判断为end_rule 并结束state 时都没有符合开始条件

        Args:
            bid_info: self.bid
        """
        if self.start:
            return
        for key in self.interrupt_bid:  # name, date, url
            if bid_info[key] == self.interrupt_bid[key] \
                    and self.interrupt_bid[key]:
                continue
            else:  # 有一个不符合条件直接返回False
                return False  # 不满足则退出判断
        logger.info(f"bid is start, start at {bid_info['name']}")
        self.start = True
        return True

    def complete(self, bid_info: dict = None):
        """ 完成任务后, newestBid 设为 stopBid, 清除 newestBid 和 interruptBid
        将 BidTask.state 设为 "complete"
        """
        logger.info("bid is end")
        self.state = "complete"
        newestBid = self.get_task("newestBid")
        if newestBid["name"]:
            self.set_task("stopBid", newestBid)
        self.set_task("newestBid", _bid_to_dict())
        self.set_task("state", "complete")
        logger.info(f"bid end at {bid_info}")
        logger.info(f"stopBid: {self.stop_bid}")

    def save_newest_and_interrupt(self, bid_info: Bid):
        """ 保存最新的招标项目信息, 设置 compelete 为 interrupt
            仅执行一次, interrupt状态下不执行
        """
        if self.interrupt:
            return
        bid_message = _bid_to_dict(bid_info)
        if len(bid_message["date"]) <= 10:
            bid_message["date"] = bid_message["date"] + " 00:00:00"
        self.set_task("newestBid", bid_message)
        self.set_task("state", "interrupt")  # 启动后状态设为interrupt
        self.newest = True
        logger.info(f"set newestBid: {bid_message}, set complete: interrupt")

    def set_interrupt_url(self, list_url):
        """设置interruptUrl
        Args:    
            list_url (str, dict): 当前访问的url信息, 在get方式下为str
            post为 dict, 由于传入的是一个新的dict而不是修改dict中的value,
            所以不用担心value可能在BidTask._get_next_list_url中改变  该注释可能有误
            TODO 验证注释
        """
        if isinstance(list_url, dict) or isinstance(list_url, list):
            self.set_task("interruptUrl", list_url.copy())
        else:
            self.set_task("interruptUrl", list_url)

    def set_interrupt(self, bid):
        """ 在BidTask._process_tag_list中调用,若开始标志(self.start==True)
        则保存 bid 到 task.interruptBid

        interrupt状态下在 self.start==True后保存
        complete状态self.start默认为True

        Args:
            bid (brows.Bid): 当前Bid对象
        """
        if self.start:
            self.set_task("interruptBid", _bid_to_dict(bid))

    def return_start_url(self) -> str or dict:
        """ 对于get方式返回str, post方式返回dict
            返回self.settings["url"]
            interrupt状态的return_start_url返回值为 self.setting
        """
        if self.interrupt:
            url = self.get_task("interruptUrl")
            url_type = "interruptUrl"
        else:
            url = self.get_task("url")
            url_type = "url"
        if not url:
            logger.error(f"{self.name}.{url_type} is empty, "
                         "please check settings json file")
            # raise
        if isinstance(url, dict):
            return deepcopy(url)
        return url

    def print_state_at_start(self):
        """ 仅在init_state时调用
        """
        logger.info(f"state = {self.state}, newest = {self.newest}, "
                    f"start = {self.start}\n"
                    f"json: newestBid = {self.get_task('newestBid')}")
        if self.state == "interrupt":
            logger.info(f"interruptUrl = {self.get_task('interruptUrl')}\n"
                        f"interruptBid = {self.get_task('interruptBid')}")

    def print_interrupt(self):
        """打印interrupt信息,仅在self.start==True状态下打印"""
        if self.start:
            logger.info(
                f"interruptBid = '{self.get_task('interruptBid.name')}', "
                f"{self.get_task('interruptBid.date')}")
        else:
            logger.info("not start")

    def compare_last_first(self, idx, bid_info: dict):
        """ 比较每页第一个项目信息是否与上一页第一个完全相等, 若相等返回True
        """
        info = tuple(bid_info.values())
        if info == self.first_bid:
            logger.info(f"open out of pages, bid is end")
            return True
        if not idx:
            self.first_bid = info
            logger.info(f"first bid: {info}")
        return False

    def bid_judge(self, bid_info: dict, idx: int):
        if self.compare_last_first(idx, bid_info) or self.stop_bid.bid_is_end(bid_info):
            self.complete(bid_info)
            return True
        if not self.newest:  # complete 状态只执行一次, interrupt状态不执行
            self.save_newest_and_interrupt(bid_info)
        return False


def _bid_to_dict(bid_prj=None):
    if isinstance(bid_prj, list):
        return {
            "name": bid_prj[0],
            "date": bid_prj[1],
            "url": bid_prj[2]
        }
    elif isinstance(bid_prj, dict):
        return {key: bid_prj[key] for key in ("name", "date", "url")}
    else:
        return {key: "" for key in ("name", "date", "url")}
