"""
task.config: nextRunTime(datetime), errorDelay(str), bidTask(list)
bidTask.config: 货物:{}
"""
import traceback
from io import TextIOWrapper

from module.bid_task import BidTask
from module.config import config
from module.exception import *
from module.get_url import GetList
from module.judge_content import titleTrie
from module.log import logger
from module.task_manager import RUN_TIME_START, TaskNode, TaskQueue
from module.utils import *
from module.web_brows import *

DATA_PATH = config.dataFolder
RE_OPEN_MAX = 4  # 异常时最大重新打开次数
SAVE_ERROR_MAX = 2  # 最多保存错误url response次数
COMPLETE_DELAY = 180  # 默认延迟时间 180分钟
ERROR_DELAY = "10m"  # 网页打开次数过多时延迟时间
NEXT_OPEN_DELAY = (2, 3)  # 默认下次打开的随机时间
RESTART_TIME = -180  # 重新运行


class BidTaskState(TaskNode):
    """
    state:
        1. complete
        2. interrupt
        3. restart
        4. error
    """
    def __init__(self, name) -> None:
        self.name = name
        nextRunTime = config.get_task(f"{name}.nextRunTime")
        self.nextRunTime = str2time(nextRunTime) if nextRunTime else \
            str2time(RUN_TIME_START)

    def set_time(self, nextRunTime: datetime):
        self.nextRunTime = nextRunTime
        config.set_task(f"{self.name}.nextRunTime", str(nextRunTime)[0: 19])


class BidTaskQueue(TaskQueue):
    task: BidTaskState = None

    def __init__(self, run_error=False):
        for name in config.get_task("TaskList"):
            task_node = BidTaskState(name)
            self.insert(task_node)

    def next_task(self) -> BidTaskState:
        if self.first_runtime() < datetime.now():
            return self.pop()
        return
    
    def restart(self):
        t: BidTaskState = self.head
        while t:
            t.nextRunTime = str2time(RUN_TIME_START)
            t = t.next


class DataFileTxt:
    filePath = {
        "list": None,
        "match": None,
        "daymatch": None,
        "daylist": None
    }
    file = {
        "list": None,
        "match": None,
        "daymatch": None,
        "daylist": None
    }

    def __init__(self, name="test") -> None:
        self.file_open = False
        self.name = name
        self._file_init(name)
        create_folder(self.filePath["list"])
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
            self.file_open = True
            self.write_all(f"{self.name} start at {date_now_s()}\n")
        logger.info(f"{self.name}.file_open={self.file_open}")

    def data_file_exit(self):
        if self.file_open:
            for v in self.file.values():
                v: TextIOWrapper
                v.close()
            self.file_open = False
        logger.info(f"{self.name}.file_open={self.file_open}")

    def write_match(self, data):
        if self.file_open:
            self._write("match", data)

    def write_list(self, data):
        if self.file_open:
            self._write("list", data)

    def _write(self, file, data):
        if not self.file_open:
            self.data_file_open()
        if "\n" in data:
            data = data.replace("\n", "")
        if data[-1] != "\n":
            data = f"{data}\n"
        for k, v in self.file.items():
            if file in k:
                v: TextIOWrapper
                v.write(data)

    def write_all(self, data):
        self.write_match(data)
        self.write_list(data)

    def flush(self):
        if self.file_open:
            for fi in self.file.values():
                fi: TextIOWrapper
                fi.flush()


class Task:
    list_url = ""
    bid_task: BidTask
    bid: Bid
    tag: BidTag
    get_list: GetList
    brows: ListBrows
    # bid_web: BidHtml
    bid_tag_error = 0
    match_num = 0  # 当次符合条件的项目个数, 仅用于日志打印
    txt: DataFileTxt
    bid_task_queue: BidTaskQueue
    error = False

    def __init__(self, name="default") -> None:
        """ 初始化任务, 保存settings 和 name
        Args:
            name(str):
        """
        settings = config.get_task("task")
        self.name = name  # 当前任务名
        logger.hr(f"init task {self.name}")
        logger.info(f"task settings:{dict2str(settings)}")
        self.next_rule = init_re(settings["next_pages"])
        self.error_delay = deep_get(settings, "errorDelay") or ERROR_DELAY
        self.complete_delay = deep_get(settings, "completeDelay") or COMPLETE_DELAY
        delay = deep_get(settings, "nextOpenDelay")
        self.delay = [int(t) for t in delay.split(",")] if delay else NEXT_OPEN_DELAY
        self.init()

    def init(self):
        self.txt = DataFileTxt(self.name)
        self.bid_task_queue = BidTaskQueue()

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
        self.get_list.config.update_referer(list_url)
        logger.info("get next pages url")
        return next_pages_url

    def process_next_list_web(self) -> bool:
        """ 打开项目列表页面,获得所有 项目的tag list, 并依次解析tag
        """
        self.match_num = 0  # 开始新网址置为0

        # 下次要打开的项目列表url
        self.get_next_list_url()

        # 打开项目列表页面, 获得 self.brows.html_list_match
        self.brows.html_cut = self.get_list.open(url=self.list_url)

        # 解析 html_list_match 源码, 遍历并判断项目列表的项目
        tagList = self.brows.get_tag_list()
        logger.info(f"len tagList = {len(tagList)}")
        self.process_tag_list(tagList)
        self.txt.flush()  # 刷新缓冲区写入文件

        if not self.match_num:
            logger.info("no match")
        if self.bid_task.state == "complete":
            self._complete_bid_task()
            return False  # state结束
        return True  # state继续

    def get_next_list_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            logger.hr("get start url")
            list_url = self.bid_task.return_start_url()
            self.list_url = self.get_list.url_extra(list_url)
        else:
            self.list_url = self.get_next_pages_url()
        page = self.get_pages()
        logger.info(f"pages: {page}, next_list_url: {self.list_url}")

    def get_pages(self):
        return self.next_rule.search(self.list_url).group()

    def tag_filterate(self):
        return True

    def process_tag_list(self, tag_list: list):
        """ 遍历处理 tag_list
        若能遍历到结尾,保存 interruptUrl 和 interrupt
        """
        logger.hr("BidTask.process_tag_list", 3)
        idx = 0
        if not tag_list:
            logger.info("tag list is []")
            self.bid_task.complete()
            return
        for idx, tag in enumerate(tag_list):
            # bid对象接收bid_tag解析结果
            if not self._bid_receive_bid_tag(tag, idx):
                continue

            if self.bid_task.bid_judge(self.bid, idx):
                break

            if not self.bid_task.start:  # interrupt状态时判断项目是否开始记录
                self.bid_task.bid_is_start(self.bid)
                continue

            if self.tag_filterate():
                self.txt.write_list(f"{self.bid.message()}\n")  # 写入文件
                self._title_trie_search(self.bid)  # 使用title trie 查找关键词
  
        logger.info(f"tag stop at {idx + 1}, tag counting from 1")
        self.bid_task.set_interrupt(self.bid)  # 设置每次最后一个为interrupt
        self.bid_task.set_interrupt_url(self.list_url)
        self.bid_task.print_interrupt()

    def _bid_receive_bid_tag(self, tag: Tag or dict, idx):
        """ 由BidTag.get 读取一个项目项目节点, Bid 接收并对信息进行处理
        """
        err_flag = False
        try:
            infoList = self.tag.get_info(tag)
            # logger.debug(str(infoList))  # 打印每次获得的项目信息
        except Exception:
            err_flag = True
            logger.error(f"tag get error: {tag},\nidx: {idx}, "
                         f"tag rule: {self.tag.rule_now}\n"
                         f"{traceback.format_exc()}")
        if not err_flag:
            try:
                self.bid.receive(*infoList)
                # logger.debug(self.bid.infoList)
            except Exception:
                err_flag = True
                logger.error(f"bid receive failed, idx: {idx}, rule: {self.bid.rule_now}, "
                             f"{traceback.format_exc()}")
        if err_flag:
            logger.error(f"error idx: {idx}")
            self.bid_tag_error += 1
            if self.bid_tag_error > 5:
                logger.error("too many bid.receive error")
                self.get_list.res.save_response(rps=self.brows.bs, url=self.list_url, save_date=True, extra="receiveError")
                raise BidReceiveError
            return False
        return True

    def _title_trie_search(self, bid_prj: Bid):
        """ 处理 bid对象

        Args:
            bid_prj (brows.Bid): 保存 bid 信息的对象
        """
        result: list = titleTrie.search_all(bid_prj.name)
        if result:
            result = f"[{','.join(result)}]; {bid_prj.message()}"
            logger.info(result)
            self.txt.write_match(result)
            self.match_num += 1

    def _complete_bid_task(self):
        self.bid_task.set_task("interruptBid.url", "")
        self.list_url = ""

    def _run_bid_task(self):
        while 1:
            result = self.process_next_list_web()
            sleep_random(self.delay, message=" you can use 'Ctrl  C' stop now")
            if not result:
                break
        logger.info(f"{self.name} {self.bid_task.name} is complete")

    def run_bid_task(self, name) -> datetime:
        self.list_url = None
        self.bid_task = BidTask(name)
        state = config.get_task(f"{name}.state")
        try:
            self._run_bid_task()
            time_add = RESTART_TIME if self.bid_task.interrupt else self.complete_delay
        except (WebTooManyVisits, TooManyErrorOpen):
            # TODO 这里需要一个文件保存额外错误日志以记录当前出错的网址, 以及上个成功打开的列表的最后一个项目
            self.bid_task.set_task("state", "error")
            logger.error(f"{traceback.format_exc()}")
            time_add = self.error_delay
            self.error = True
        if state in ("error", "interrupt") and self.bid_task.state == "complete":
            return str2time(RUN_TIME_START)
        return datetime.now() + get_time_add(time_add)

    def run(self, restart=False) -> datetime:
        logger.hr(f"{self.name} run")
        if not self.txt.file_open:
            self.txt.data_file_open()
        if restart:
            self.bid_task_queue.restart()
        while 1:
            self.bid_task_queue.print()
            bid_task: BidTaskState = self.bid_task_queue.next_task()
            if not bid_task:
                logger.info("no bid task ready")
                break
            logger.hr(f"bid task: {self.name} {bid_task.name}", 2)
            nextRunTime = self.run_bid_task(bid_task.name)
            bid_task.set_time(nextRunTime)
            config.save()
            self.bid_task_queue.insert(bid_task)
        self.close()
        if not self.error:
            reset_task(config, self.name, set_time=True, time=time2str(self.bid_task_queue.head.nextRunTime))
        return self.bid_task_queue.first_runtime(), self.error

    def close(self):
        self.txt.data_file_exit()
        self.get_list.s.close()


if __name__ == "__main__":
    config.name = "zgzf"
    from module.web.zgzf import Task
    self = Task(config.name)
    self.run()
