"""
任务类
包含三个类:
1. State : 表示Task在普通情况下, 上次运行无记录,或上次运行完成
2. InterruptState : 表示Task 上次运行时中断
3. Task : 表示任务, 保存有该任务所必须的规则, 能爬取完一个具体的网站
"""
import traceback
from copy import deepcopy
from datetime import datetime
from importlib import import_module
from io import TextIOWrapper

from module import config
from module.get_url import GetList
from module.judge_content import titleTrie
from module.log import logger
from module.utils import *
from module.web_brows import *
from module.web_exception import WebTooManyVisits

DATA_PATH = config.dataFolder
RE_OPEN_MAX = 4  # 异常时最大重新打开次数
SAVE_ERROR_MAX = 2  # 最多保存错误url response次数


class PageList:
    def __init__(self):
        """ 保存PageQueue, PageWait

        """
        settings = config.get_task()
        self.queue: list = deep_get(settings, "PageQueue")
        self.wait: list = deep_get(settings, "PageWait")
        # self.now = self.queue[0]

    def restart(self):
        """ 将json中 complete 添加到 queue中
        """
        logger.hr("BidTask.restart", 3)
        for page in self.wait:
            self.queue.append(page)
        for page in self.queue:
            config.set_task(f"{page}.error", False)
        config.set_task("PageWait", [])
        self.wait = config.get_task("PageWait")
        logger.info(f"PageQueue: {self.queue}")

    def queue_is_empty(self):
        if self.queue:
            return False
        return True

    def queue_move(self):
        """将Queue第一个移到Wait"""
        self.wait.append(self.queue.pop(0))
        return self.queue.copy(), self.wait.copy()


# 状态的切换
# 当满足end rule时,
class Complete:
    newest = False
    start = True  # process_tag_list 中判断
    state = ""  # 默认为 ""

    def __init__(self, settings, urlTask="test") -> None:
        self.end_rule = settings["end_rule"]  # 翻页结束标志
        self.urlTask = urlTask
        self.settings = settings
        self.init()

    def init(self):
        """ 判断 end_rule 是否合法
        """
        date_6 = date_days(change_days=-6)
        if not self.end_rule["date"]:
            self.end_rule["date"] = date_6
        if len(self.end_rule["date"]) <= 10:
            self.end_rule["date"] = self.end_rule["date"] + " 00:00:00"
        if time_difference(self.end_rule["date"], date_days(), "day") < -6:
            logger.info(f"end_rule: {self.end_rule['date']} is beyond 6 days")
            self.end_rule["date"] = date_6
            deep_set(self.settings, "end_rule.date", date_6)
        logger.info(f"json: {self.urlTask}.complete = "
                    f"\"{deep_get(self.settings, 'complete')}"
                    f"\"\nend_rule : {self.end_rule}")

    def _date_is_end(self, date: str, date_len):
        """ 判断传入的date是否符合 end_date要求
        """
        if date_len > 10:
            date_format = "%Y-%m-%d %H:%M:%S"
            end_date = self.end_rule["date"]
        else:
            date_format = "%Y-%m-%d"
            end_date = self.end_rule["date"][:10]
        return \
            datetime.strptime(date, date_format) < \
            datetime.strptime(end_date, date_format)

    def bid_is_end(self, bid_prj: BidBase):
        """ 判断当前项目是否符合结束条件
        Args:
            bid_prj (<class> BidBase): 当前Bid对象, 保存项目信息
        """
        # 名称和Url都相同时停止
        if bid_prj.name == self.end_rule["name"] \
                and bid_prj.url == self.end_rule["url"]:
            return True
        # 超出时间限制时停止
        if self.end_rule["date"]:
            if self._date_is_end(bid_prj.date, len(bid_prj.date)):
                return True
        return False

    def bid_is_start(self, *args):
        # 仅在 interrupt状态进行判断
        pass

    def complete(self):
        """ 完成任务后, 将newest 设为 end_rule, 清除 newest 和 interrupt设置
        将 BidTask.State.state 设为 "complete"
        """
        logger.info("bid is end")
        self.state = "complete"
        if deep_get(self.settings, "newest.name"):
            deep_set(self.settings, "end_rule", self.settings["newest"])
        deep_set(self.settings, "newest", _bid_to_dict())
        deep_set(self.settings, "interrupt", _bid_to_dict())
        deep_set(self.settings, "interruptUrl", "")
        deep_set(self.settings, "complete", "complete")

    def save_newest_and_interrupt(self, bid: BidBase):
        """ 保存最新的招标项目信息, 设置 compelete 为 interrupt
            仅执行一次, interrupt状态下不执行
        """
        bid_message = _bid_to_dict(bid)
        bid_message["date"] = date_now_s()
        deep_set(self.settings, "newest", bid_message)
        deep_set(self.settings, "complete", "interrupt")  # 启动后状态设为interrupt
        self.newest = True
        logger.info(f"set newest: {bid_message}, "
                    f"set complete: {deep_get(self.settings, 'complete')}")

    def set_interrupt_url(self, list_url):
        """设置interruptUrl
        Args:    
            list_url (str, dict): 当前访问的url信息, 在get方式下为str
            post为 dict, 由于传入的是一个新的dict而不是修改dict中的value,
            所以不用担心value可能在BidTask._get_next_list_url中改变  该注释可能有误
            TODO 验证注释
        """
        if isinstance(list_url, dict) or isinstance(list_url, list):
            deep_set(self.settings, "interruptUrl", list_url.copy())
        else:
            deep_set(self.settings, "interruptUrl", list_url)

    def set_interrupt(self, bid):
        """ 在BidTask._process_tag_list中调用,若开始标志(self.start==True)
        则保存 bid 到 self.settings["interrupt"]
        
        interrupt状态下在 self.start==True后保存
        complete状态self.start默认为True
        
        Args:
            bid (brows.BidBase): 当前Bid对象
        """
        if self.start:
            deep_set(self.settings, "interrupt", _bid_to_dict(bid))

    def return_start_url(self) -> str or dict:
        """ 对于get方式返回str, post方式返回dict
            返回self.settings["url"]
            interrupt状态的return_start_url返回值为 self.setting
        """
        if self.settings["url"]:
            url = self.settings["url"]
            if isinstance(url, dict):
                return deepcopy(url)
            return url
        else:
            logger.error(f"{self.urlTask}.url: is empty, "
                            "please check settings json file")
            exit()

    def print_state_at_start(self):
        """ 仅在init_state时调用
        """
        logger.info(f"state = {self.state}, newest = {self.newest}, "
                    f"start = {self.start}\n"
                    f"json: newest = {self.settings['newest']}")
        if self.state == "interrupt":
            logger.info(f"interruptUrl = {self.settings['interruptUrl']}\n"
                        f"interrupt = {jsdump(self.settings['interrupt'])}")

    def print_interrupt(self):
        """打印interrupt信息,仅在self.start==True状态下打印"""
        if self.start:
            logger.info(
                f"interrupt.name = '{self.settings['interrupt']['name']}', "
                f"{self.settings['interrupt']['date']}")
        else:
            logger.info("not start")


class InterruptState(Complete):
    state = "interrupt"

    def __init__(self, settings, urlTask="test"):
        super().__init__(settings, urlTask)
        self.interrupt = self.settings["interrupt"]
        self.newest = True
        self.start = False

        if not deep_get(self.settings, "interrupt.name"):
            logger.error(f"{self.urlTask}.interrupt.name is empty, "
                            "please check settings json file")
            exit()

    def bid_is_start(self, bid_prj: BidBase) -> True:
        """判断条件为: name, date, url 三个信息必须全部符合, 符合返回True 并
        将 self.state 置为 True, 若有一个不符合则返回 False .
        仅在 interrupt状态下执行
        
        注意: json中state.interrupt 信息为自动生成, 
        若手动填写请注意是否填写正确,否则可能导致一直跳过当前招标项目,
        直到判断为end_rule 并结束state 时都没有符合开始条件
        
        Args:
            bid_prj: self.bid
        """
        for key in self.interrupt:  # name, date, url
            if getattr(bid_prj, key) == self.interrupt[key] \
                    and self.interrupt[key]:
                continue
            else:  # 有一个不符合条件直接返回False
                return False  # 不满足则退出判断
        logger.info(f"bid is start, start at {bid_prj.name}")
        self.start = True
        return True

    def save_newest(self, *args):
        # interrupt状态不执行
        pass

    def save_newest_and_set_interrupt(self, *args):
        # interrupt状态不执行
        pass

    def return_start_url(self) -> str or dict:
        """ interrupt状态返回 self.settings["interruptUrl"]
        """
        if self.settings["interruptUrl"]:
            return self.settings["interruptUrl"]
        else:
            logger.error(f"{self.urlTask}.interruptUrl: is empty, "
                         "please check settings json file")
            exit()


def TaskState_init(urlTask) -> Complete or InterruptState:
    """根据传入settings返回对应的class"""
    settings = config.get_task(f"{urlTask}")
    if settings["complete"] == "interrupt":
        return InterruptState(settings, urlTask)
    else:
        return Complete(settings, urlTask)


class DataFileTxt:
    filePath = {
        "list": None,
        "match": None,
        "dayMatch": None,
        "dayList": None
    }
    file = {
        "list": None,
        "match": None,
        "dayMatch": None,
        "dayList": None
    }

    def __init__(self, name="test") -> None:
        self.file_open = False
        self.name = name
        self._file_init(name)
        creat_folder(self.filePath["list"])
        log = ""
        for k, v in self.filePath.items():
            log += f"{k}: {v}\n{' '*26}"
        logger.info(log.strip())

    def _file_init(self, name):
        for k in self.filePath.keys():
            if "day" in k:
                self.filePath[k] = f"{DATA_PATH}/bid_{k}_{date_days(format='day')}.txt"
            else:
                self.filePath[k] = f"{DATA_PATH}/bid_{k}_{name}.txt"

    def data_file_open(self):
        if not self.file_open:
            for k, v in self.filePath.items():
                self.file[k] = open(v, "a", encoding="utf-8")
            # 写入运行时间
            self.write_all(f"{self.name} start at {date_now_s()}\n")
            self.file_open = True
        logger.info(f"{self.name}.file_open={self.file_open}")

    def data_file_exit(self):
        if self.file_open:
            for v in self.file.values():
                v: TextIOWrapper
                v.close()
            self.file_open = False
        logger.info(f"{self.name}.file_open={self.file_open}")

    def write_match(self, data):
        self._write("match", data)

    def write_list(self, data):
        self._write("list", data)

    def _write(self, file, data):
        if data[-1] != "\n":
            data = f"{data}\n"
        for k, v in self.file.items():
            if file.title() in k:
                v: TextIOWrapper
                v.write(data)

    def write_all(self, data):
        self.write_match(data)
        self.write_list(data)


NEXT_OPEN_DELAY = (2, 3)  # 默认下次打开的随机时间


class BidTaskInit:
    list_url = ""
    urlTask: str  # "公开招标" "邀请招标"
    State: Complete or InterruptState
    bid: BidBase
    tag: BidTag
    get_list: GetList
    brows: ListBrows
    # bid_web: BidHtml
    bid_tag_error = 0
    match_num = 0  # 当次符合条件的项目个数, 仅用于日志打印
    error_open = True
    file_open = False

    def __init__(self, name="test") -> None:
        """ 初始化任务, 保存settings 和 name
        Args:
            name(str): 
        """
        settings = config.get_task()
        self.name = name  # 当前任务名
        self.txt = DataFileTxt(name)
        self.page_list = PageList()
        self.error_delay = deep_get(settings, "OpenConfig.errorDelay")
        delay = deep_get(settings, "OpenConfig.nextOpenDelay")
        self.delay = [int(t) for t in delay.split(",")] \
            if delay else NEXT_OPEN_DELAY
        self.next_rule = init_re(settings["OpenConfig"]["next_pages"])
        logger.info(f"init task {self.name}, list brows:\n"
                    f"url settings:\n{dict2str(settings['OpenConfig'])}\n")

    def init_state(self):
        """ 用_get_url_task 判断 task.PageQueue 中是否还有state
        有则用 TaskState.init() 初始化State, 如果State已初始化将会被新的覆盖
        无则返回 False

        Returns:
            (bool): 初始化完成返回 True ,失败返回 False 
        """
        logger.hr(f"{self.name}.init_state", 3)
        # 若queue中还有state
        if not self.page_list.queue_is_empty():
            self.urlTask = self.page_list.queue[0]
            logger.info(f"{self.name}._get_url_task = {self.urlTask}")
            self.State = TaskState_init(self.urlTask)
            self.State.print_state_at_start()
            self.txt.write_all(f"{self.urlTask}\n")
            self.list_url = ""
            return True
        logger.info(f"{self.name}.queue is []")
        return False


class BidTask(BidTaskInit):
    task_end = False  # 由 pywebio设置
    urlTask = ""

    def get_next_pages_url(self, list_url="", next_rule=None, **kwargs) -> str:
        """
        Args:
            list_url (str): 项目列表网址
            next_rule (str): 项目列表网址下一页规则,仅在测试时使用
        Returns:
            next_pages_url (str): 即将打开的url
        """
        next_rule = next_rule if next_rule else self.next_rule
        if isinstance(next_rule, str):
            next_rule = re.compile(next_rule)
        if not list_url:
            list_url = self.list_url
        pages = str(int(next_rule.search(list_url).group()) + 1)
        next_pages_url = next_rule.sub(pages, list_url)
        logger.info(f"pages: {pages}")
        return next_pages_url

    def process_next_list_web(self) -> bool:
        """ 打开项目列表页面,获得所有 项目的tag list, 并依次解析tag
        """
        logger.info("BidTask.get_url_list")
        self.match_num = 0  # 开始新网址置为0

        # 下次要打开的项目列表url
        self._get_next_list_url()

        # 打开项目列表页面, 获得 self.brows.html_list_match
        self.brows.html_cut = self.get_list.open(url=self.list_url)

        # 解析 html_list_match 源码, 遍历并判断项目列表的项目
        tagList = self.brows.get_tag_list()
        # if not tagList:
        #     self._complete_page_task()
        #     logger.warning("tag list is []")
        #     return False
        self._process_tag_list(tagList)

        if not self.match_num:
            logger.info("no match")
        if self.State.state == "complete":
            self._complete_page_task()
            return False  # state结束
        return True  # state继续

    def _get_next_list_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            list_url = self.State.return_start_url()
            self.list_url = self.get_list.url_extra(list_url)
        else:
            self.list_url = self.get_next_pages_url()
        logger.info(f"next_list_url: {self.list_url}")

    def _process_tag_list(self, tag_list: list):
        """ 遍历处理 tag_list
        若能遍历到结尾,保存 interruptUrl 和 interrupt
        """
        logger.hr("BidTask.process_tag_list", 3)
        idx = 0
        for idx, tag in enumerate(tag_list):
            # bid对象接收bid_tag解析结果
            if not self._bid_receive_bid_tag(tag, idx):
                continue
            if not idx and self.brows.compare_last_first(self.bid.infoList):
                self.State.complete()
                logger.info(f"open out of pages, pages now is {self.list_url}")
                break
            if self.State.bid_is_end(self.bid):  # 判断是否符合结束条件
                self.State.complete()  # set self.State.state = "complete"
                logger.info(f"bid end at {self.bid.infoList}")
                logger.info(f"end_rule: {self.State.end_rule}")
                if idx == 0:
                    logger.info(f"idx = {idx}, tag now: {self.bid.infoList}")
                break
            if not self.State.newest:  # complete 状态只执行一次,interrupt状态该语句结果为False
                self.State.save_newest_and_interrupt(self.bid)
            if not self.State.start:  # interrupt状态时判断项目是否开始记录
                self.State.bid_is_start(self.bid)
                continue

            self.State.set_interrupt(self.bid)  # 设置每次最后一个为interrupt
            self.txt.write_list(f"{self.bid.message()}\n")  # 写入文件
            self._title_trie_search(self.bid)  # 使用title trie 查找关键词
        logger.info(f"tag stop at {idx + 1}, tag counting from 1")
        self.State.set_interrupt_url(self.list_url)
        self.State.print_interrupt()

    def _bid_receive_bid_tag(self, tag: Tag or dict, idx):
        """ 由BidTag.get 读取一个项目项目节点, BidBase 接收并对信息进行处理
        """
        err_flag = False
        try:
            infoList = self.tag.get(tag)
            # logger.debug(str(infoList))  # 打印每次获得的项目信息
        except Exception:
            err_flag = True
            logger.error(f"tag get error: {tag},\nidx: {idx}"
                         f"tag rule: {self.tag.rule_now}\n"
                         f"{traceback.format_exc()}")
        if not err_flag:
            try:
                self.bid.receive(*infoList)
                # logger.debug(self.bid.infoList)
            except Exception:
                err_flag = True
                logger.error(f"bid receive failed, idx: {idx}, rule: {self.bid.rule_now}"
                             f"{traceback.format_exc()}")
        if err_flag:
            logger.error(f"error idx: {idx}")
            self.bid_tag_error += 1
            if self.bid_tag_error > 5:
                logger.error("too many bid.receive error")
                self.get_list.res.save_response(
                    rps=self.brows.bs,
                    save_date=True, extra="receiveError")
                raise KeyboardInterrupt
            return False
        return True

    def _title_trie_search(self, bid_prj: BidBase):
        """ 处理 bid对象

        Args:
            bid_prj (brows.BidBase): 保存 bid 信息的对象
        """
        result: list = titleTrie.search_all(bid_prj.name)
        if result:
            result = f"[{','.join(result)}]; {bid_prj.message()}"
            logger.info(result)
            self.txt.write_match(result)
            self.match_num += 1

    def _complete_page_task(self):
        """ 将json中 queue 头元素出队,添加到complete中
        """
        # PageQueue, PageWait = self._state_queue_move()
        PageQueue, PageWait = self.page_list.queue_move()
        logger.info(f"{self.urlTask} complete, PageQueue: {PageQueue}\n"
                    f"PageWait: {PageWait}")
        if PageQueue:
            self.urlTask = PageQueue[0]

    def set_error_state(self):
        """当网页打开次数过多时设置错误标志,并将当前state移到stateWait"""
        config.set_task(
                 f"{self.urlTask}.error", f"{self.State.state}Error")
        # self._state_queue_move()
        self.page_list.queue_move()


def _bid_to_dict(bid_prj=None):
    if isinstance(bid_prj, list):
        return {
            "name": bid_prj[0],
            "date": bid_prj[1],
            "url": bid_prj[2]
        }
    elif isinstance(bid_prj, dict):
        return bid_prj
    elif isinstance(bid_prj, BidBase):
        return {
            "name": bid_prj.name,
            "date": bid_prj.date,
            "url": bid_prj.url
        }
    else:
        return {key: "" for key in ("name", "date", "url")}


if __name__ == "__main__":
    json_file = "./bid_settings/bid_settings_test.json"
    json_set = read_json(json_file)
    bid_task_name = "qjc"
    bid_task_test = BidTask(json_set[bid_task_name])

    # test code
    try:
        # bid_task_test.restart()
        bid_task_test.init_state()
        while 1:
            state_result = bid_task_test.process_next_list_web()
            if state_result:
                sleep_random(message=" you can use 'Ctrl  C' stop now")
                # yield True
            else:
                logger.info(f"{bid_task_test.name} {bid_task_test.urlTask} is complete")
                break
    # use Ctrl + C exit
    except(KeyboardInterrupt, Exception) as error:
        save_json(json_set, json_file)
        print(error)
