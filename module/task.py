"""
任务类
包含三个类:
1. State : 表示Task在普通情况下, 上次运行无记录,或上次运行完成
2. InterruptState : 表示Task 上次运行时中断
3. Task : 表示任务, 保存有该任务所必须的规则, 能爬取完一个具体的网站
"""
import traceback
from datetime import datetime

from bs4 import Tag

from module.judge_content import title_trie
from module.log import logger
from module.utils import *
from module.web_brows import *
from module.web_exception import WebTooManyVisits

DATA_PATH = r"./data"
RE_OPEN_MAX = 6  # 异常时最大重新打开次数
SAVE_ERROR_MAX = 2  # 最多保存错误url response次数


class BidState:
    class Complete:
        newest = False
        start = True  # process_tag_list 中判断
        state = ""  # 默认为 ""

        def __init__(self, settings, state_idx="test") -> None:
            self.end_rule = settings["end_rule"]  # 翻页结束标志
            self.state_idx = state_idx
            self.settings = settings
            self.init()

        def init(self):
            """ 判断 end_rule 是否合法
            """
            if not self.end_rule["date"]:
                self.end_rule["date"] = date_days(change_days=-6)
            if len(self.end_rule["date"]) <= 10:
                self.end_rule["date"] = self.end_rule["date"] + " 00:00:00"
            # TODO end_rule 和现在的日期不能超过6天,若超过,则修改为与现在日期差6天的值
            logger.info(f"json: {self.state_idx}.complete = "
                        f"\"{deep_get(self.settings, 'complete')}"
                        f"\"\nend_rule : {self.end_rule}")

        def _date_is_end(self, date: str, date_len):
            """ 判断传入的date是否符合 end_date要求
            """
            if date_len > 10:
                date_format = "%Y-%m-%d %H:%M:%S"
                end_date = self.end_rule["date"]
            elif date_len <= 10:
                date_format = "%Y-%m-%d"
                end_date = self.end_rule["date"][:10]
            return datetime.strptime(date, date_format) < \
                   datetime.strptime(end_date, date_format)

        def bid_is_end(self, bid_prj: BidProject.Bid):
            """ 判断当前项目是否符合结束条件
            Args:
                bid_prj (<class> BidProject.Bid): 当前Bid对象, 保存项目信息
            """
            if bid_prj.name == self.end_rule["name"] \
                    and bid_prj.url == self.end_rule["url"]:
                return True
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

        def save_newest_and_interrupt(self, bid: BidProject.Bid):
            """ 保存最新的招标项目信息, 设置 compelete 为 interrupt
                仅执行一次, interrupt状态下不执行
            """
            bid_message = _bid_to_dict(bid)
            bid_message["date"] = date_now_s()
            deep_set(self.settings, "newest", bid_message)
            deep_set(self.settings, "complete", "interrupt")  # 启动后状态设为interrupt
            self.newest = True

        def set_interrupt_url(self, list_url):
            """设置interruptUrl"""
            if isinstance(list_url, dict) or isinstance(list_url, list):
                deep_set(self.settings, "interruptUrl", list_url.copy())
            else:
                deep_set(self.settings, "interruptUrl", list_url)
        
        def set_interrupt(self, list_url, bid):
            """ 在BidTask._process_tag_list中调用,若开始标志(self.start==True)
            则保存list_url 到 self.settings["interruptUrl"]
            保存  bid 到 self.settings["interrupt"]
            
            interrupt状态下在 self.start==True后保存
            complete状态self.start默认为True
            
            Args:
                list_url (str, dict): 当前访问的url信息, 在get方式下为str
                    post为 dict, 由于传入的是一个新的dict而不是修改dict中的value,
                    所以不用担心value可能在BidTask._get_next_list_url中改变
                bid (web_brows.BidProject.Bid): 当前Bid对象
            """
            if self.start:
                self.set_interrupt_url(list_url)
                deep_set(self.settings, "interrupt", _bid_to_dict(bid))

        def return_start_url(self) -> str or dict:
            """ 对于get方式返回str, post方式返回dict
                返回self.settings["url"]
                interrupt状态的return_start_url返回值为 self.setting
            """
            if self.settings["url"]:
                return self.settings["url"]
            else:
                logger.error(f"{self.state_idx}.url: is empty, "
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

    class InterruptState(Complete):
        state = "interrupt"

        def __init__(self, settings, state_idx="test"):
            super().__init__(settings, state_idx)
            self.interrupt = self.settings["interrupt"]
            self.newest = True
            self.start = False

            if not deep_get(self.settings, "interrupt.name"):
                logger.error(f"{self.state_idx}.interrupt.name is empty, "
                             "please check settings json file")
                exit()

        def bid_is_start(self, bid_prj: BidProject.Bid) -> True:
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
                        and not self.interrupt[key]:
                    continue
                else:  # 有一个不符合条件直接返回False
                    return False  # 不满足则退出判断
            logger.info("bid is start")
            self.start = True
            return True

        def save_newest(self, *args):
            # interrupt状态不执行
            pass

        def save_newest_and_set_interrupt(self):
            # interrupt状态不执行
            pass

        def return_start_url(self) -> str or dict:
            """ interrupt状态返回 self.settings["interruptUrl"]
            """
            if self.settings["interruptUrl"]:
                return self.settings["interruptUrl"]
            else:
                logger.error(f"{self.state_idx}.interruptUrl: is empty, "
                             "please check settings json file")
                exit()

    @classmethod
    def init(cls, settings, state_idx) -> Complete or InterruptState:
        """根据传入settings返回对应的class"""
        if settings["complete"] == "interrupt":
            return cls.InterruptState(settings, state_idx)
        else:
            return cls.Complete(settings, state_idx)


class BidTaskInit:
    state_idx: str  # init at _get_state  "state1" or "state2"
    State: BidState.Complete or BidState.InterruptState
    bid: BidProject.Bid
    bid_tag: BidTag
    web_brows: ListWebBrows.Html
    bid_web: BidHtml
    tag_list = None  # 源码解析后的 list
    list_file = None
    match_list_file = None
    list_url: str = None
    bid_tag_error = 0
    error_open = True
    

    def __init__(self, settings, task_name="test", test=False) -> None:
        self.settings = settings  # zzlh:{}
        self.task_name = task_name  # 当前任务名
        self.match_num = 0  # 当次符合条件的项目个数, 仅用于日志打印
        self.nextRunTime = settings["nextRunTime"]
        self.error_delay = deep_get(self.settings, "urlConfig.errorDelay")
        self.delay = deep_get(self.settings, "urlConfig.nextOpenDelay")
        if self.delay:
            self.delay = [int(t) for t in self.delay.split(",")]
        self._init_brows(settings)
        self._creat_data_file(test)
        logger.info(f"init task {self.task_name}, list brows:\n"
                    f"url settings:\n{str_dict(settings['urlConfig'])}\n"
                    f"rule:\n{str_dict(settings['rule'])}")

    def _init_brows(self, settings):
        """ 初始化网页对象模型, 只在初始化时调用一次
        
        Args:
            settings (dict): json中 的具体任务
        """
        self.bid_tag = BidTag(settings)
        self.bid = BidProject.init(settings, self.task_name)
        self.web_brows = ListWebBrows.init(settings, self.task_name)
        self.bid_web = BidHtml(settings)

    def _creat_data_file(self, test=False):
        """ 创建数据保存文件, add 方式
        Args:
            test (bool): 测试开关,仅在测试中使用
        """
        file = "test" if test else self.task_name
        list_save = f"{DATA_PATH}/bid_list_{file}.txt"
        match_list_save = f"{DATA_PATH}/bid_match_list_{file}.txt"
        creat_folder(list_save)
        self.list_file = open(list_save, "a", encoding="utf-8")
        self.match_list_file = open(match_list_save, "a", encoding="utf-8")
        # 写入一行运行时间
        self.list_file.write(f"start at {date_now_s()}\n")
        self.match_list_file.write(f"start at {date_now_s()}\n")

    def _get_state_idx(self, queue: list):
        """ 从stateQueue中取第一个state 赋给 self.state_idx(str)
        若 queue 为空返回False
        """
        if queue:
            self.state_idx = queue[0]
            logger.info(f"{self.task_name}._get_state_idx = {self.state_idx}")
            return True
        else:
            logger.info(f"{self.task_name}.queue is []")
            return False

    def init_state(self):
        """ 用_get_state_idx 判断 task.stateQueue 中是否还有state
        有则用 BidState.init() 初始化State, 如果State已初始化将会被新的覆盖
        无则返回 False
        
        Returns:
            (bool): 初始化完成返回 True ,失败返回 False 
        """
        logger.hr(f"{self.task_name}.init_state", 3)
        # 若queue中还有state
        if self._get_state_idx(deep_get(self.settings, "stateQueue")):
            self.State = BidState.init(
                self.settings[self.state_idx], self.state_idx)
            self.State.print_state_at_start()

            self.list_file.write(f"{self.state_idx}\n")
            self.match_list_file.write(f"{self.state_idx}\n")
            self.list_url = None

            return True
        return False


class BidTask(BidTaskInit):
    task_end = False  # 由 pywebio设置

    def close(self):
        """关闭已打开的文件,一般在程序结束时使用"""
        self.list_file.close()
        self.match_list_file.close()

    def restart(self):
        """ 将json中 complete 添加到 queue中
        """
        logger.hr("BidTask.restart", 3)
        queue = deep_get(self.settings, "stateQueue")
        complete = deep_get(self.settings, "stateWait")
        queue += complete
        deep_set(self.settings, "stateWait", [])
        for state in queue:
            deep_set(self.settings, f"{state}.error", False)
        logger.info(f"stateQueue: {queue}")

    def process_next_list_web(self):
        """ 打开项目列表页面,获得所有 项目的tag list, 并依次解析tag
        """
        logger.info("BidTask.get_url_list")
        self.match_num = 0  # 开始新网址置为0

        # 下次要打开的项目列表url
        self._get_next_list_url()

        # 打开项目列表页面, 获得 self.web_brows.html_list_match
        self._open_list_url(self.list_url)

        # 解析 html_list_match 源码, 遍历并判断项目列表的项目
        self.tag_list = self.web_brows.get_tag_list()
        if not self.tag_list:
            self._complete_state()
            logger.warning("tag list is []")
            return False
        self._process_tag_list()

        if not self.match_num:
            logger.info("no match")
        if self.State.state == "complete":
            self._complete_state()
            return False  # state结束
        return True  # state继续

    def _get_next_list_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            list_url = self.State.return_start_url()
            self.list_url = self.web_brows.url_extra(list_url)
        else:
            self.list_url = self.web_brows.get_next_pages(self.list_url)

    # TODO 写的很*,记得重写, 且需要改成重试次数过多(6次以上)后将任务延迟
    def _open_list_url(self, url, reOpen=0, save_error=0):
        """ 封装web_brows行为,打开浏览页面，获得裁剪后的页面源码
        """
        if self.task_end:  # webio将task_end置为True后中断
            from bid_run import bidTaskManager
            bidTaskManager.web_break()
        logger.hr("BidTask._open_list_url", 3)
        self.error_open = False
        cookie = self.web_brows.set_cookie()
        if cookie:
            deep_set(self.settings, "headers.Cookie", cookie)
        try:
            self.web_brows.open(url=url)
        except AssertionError:
            # TODO 识别出错的网页
            logger.error(f"{traceback.format_exc()}")
            self.error_open = True
        else:
            try:  # 在打开网页后判断网页源码是否符合要求
                self.web_brows.html_cut = self.web_brows.cut_html()
            except Exception:
                self.error_open = True
                if save_error < SAVE_ERROR_MAX:
                    self.web_brows.save_response(
                        save_date=True, extra="cut_Error")
                    logger.info(f"cut html error")                                
        if self.error_open:
            if self.web_brows.too_many_open():
                raise WebTooManyVisits
            if reOpen < RE_OPEN_MAX:
                reOpen += 1
                sleep_random((2, 3))
                logger.info(f"open \n{self.list_url}\n"
                            f"again, reOpen: {reOpen + 1}")
                self._open_list_url(url, reOpen, save_error)

            assert reOpen < RE_OPEN_MAX, \
                f"{self.list_url} open more than {RE_OPEN_MAX} time"

    def _process_tag_list(self):
        """ 遍历处理 self.tag_list
        若能遍历到结尾,保存 interruptUrl 和 interrupt
        """
        logger.hr("BidTask.process_tag_list", 3)
        for idx, tag in enumerate(self.tag_list):
            # bid对象接收bid_tag解析结果
            if not self._bid_receive_bid_tag(tag, idx):
                continue
            if not idx and self.web_brows.compare_last_first(self.bid.message):
                self.State.complete()
                logger.info(f"open out of pages, pages now is {self.list_url}")
                break
            if self.State.bid_is_end(self.bid):  # 判断是否符合结束条件
                self.State.complete()  # set self.State.state = "complete"
                logger.info(f"bid end at {self.bid.message}")
                logger.info(f"end_rule: {self.State.end_rule}")
                break
            if not self.State.newest:  # 非interrupt 状态只执行一次,interrupt状态该语句结果为False
                self.State.save_newest_and_interrupt(self.bid)
            if not self.State.start:  # interrupt状态时判断项目是否开始记录
                if not self.State.bid_is_start(self.bid):
                    self.State.set_interrupt_url(self.list_url)
                    continue

            self.State.set_interrupt(self.list_url, self.bid)  # 设置每次最后一个为interrupt
            self.list_file.write(f"{str(self.bid.message)}\n")  # 写入文件
            self._title_trie_search(self.bid)  # 使用title trie 查找关键词
        logger.info(f"tag stop at {idx + 1}")
        self.State.print_interrupt()

    def _bid_receive_bid_tag(self, tag: Tag or dict, idx):
        """ 由BidTag.get 读取一个项目项目节点, BidProject.Bid 接收并对信息进行处理
        """
        err_flag = False
        try:
            message = self.bid_tag.get(tag)
            # logger.debug(str(message))  # 打印每次获得的项目信息
        except Exception:
            err_flag = True
            logger.error(f"tag get error: {tag},\nidx: {idx}"
                         f"bid_tag rule: {self.bid_tag.rule_now}\n"
                         f"{traceback.format_exc()}")
        if not err_flag:
            try:
                self.bid.receive(*message)
                # logger.debug(self.bid.message)
            except Exception:
                err_flag = True
                logger.error(f"bid receive failed, idx: {idx}, rule: {self.bid.rule_now}"
                             f"{traceback.format_exc()}")
        if err_flag:
            logger.error(f"error idx: {idx}")
            self.bid_tag_error += 1
            if self.bid_tag_error > 5:
                logger.error("too many bid.receive error")
                self.web_brows.save_response(
                    rps=self.web_brows.bs,
                    save_date=True, extra="receiveError")
                raise KeyboardInterrupt
            return False
        return True

    def _title_trie_search(self, bid_prj: BidProject.Bid):
        """ 处理 bid对象

        Args:
            bid_prj (web_brows.BidProject.Bid): 保存 bid 信息的对象
        """
        result: list = title_trie.search_all(bid_prj.name)
        if result:
            logger.info(f"{result} {self.bid.message}")
            result.append(bid_prj.message)
            self.match_list_file.write(f"{str(result)}\n")
            self.match_num += 1

    def _state_queue_move(self):
        """将stateQueue第一个移到stateWait"""
        queue = deep_get(self.settings, "stateQueue")
        complete = deep_get(self.settings, "stateWait")
        complete.append(queue.pop(0))
        deep_set(self.settings, "stateQueue", queue)
        deep_set(self.settings, "stateWait", complete)
        return queue, complete

    def _complete_state(self):
        """ 将json中 queue 头元素出队,添加到complete中
        """
        stateQueue, stateWait = self._state_queue_move()
        logger.info(f"{self.state_idx} complete, stateQueue: {stateQueue}\n"
                    f"stateWait: {stateWait}")
        if stateQueue:
            self.state_idx = stateQueue[0]

    def set_error_state(self):
        """当网页打开次数过多时设置错误标志,并将当前state移到stateWait"""
        deep_set(self.settings,
                 f"{self.state_idx}.error", f"{self.State.state}Error")
        self._state_queue_move()


def _bid_to_dict(bid_prj=None):
    if isinstance(bid_prj, list):
        return {
            "name": bid_prj[0],
            "date": bid_prj[1],
            "url": bid_prj[2]
        }
    elif isinstance(bid_prj, dict):
        return bid_prj
    elif isinstance(bid_prj, BidProject.Bid):
        return {
            "name": bid_prj.name,
            "date": bid_prj.date,
            "url": bid_prj.url
        }
    else:
        return {key: "" for key in ("name", "date", "url")}


if __name__ == "__main__":
    json_file = "./bid_settings/bid_settings.json"
    json_set = read_json(json_file)
    bid_task_name = "zgzf"
    bid_task_test = BidTask(json_set[bid_task_name], bid_task_name)

    # test code
    try:
        bid_task_test.restart()
        bid_task_test.init_state()
        while 1:
            state_result = bid_task_test.process_next_list_web()
            if state_result:
                sleep_random(message=" you can use 'Ctrl  C' stop now")
                # yield True
            else:
                logger.info(f"{bid_task_test.task_name} {bid_task_test.state_idx} is complete")
                break
    # use Ctrl + C exit
    except(KeyboardInterrupt, Exception):
        save_json(json_set, json_file)
