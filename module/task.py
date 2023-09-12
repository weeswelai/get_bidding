"""

"""
import traceback
from io import TextIOWrapper

from module.bid_task import BidTask
from module.config import CONFIG
from module.exception import *
from module.get_url import GetList
from module.judge_content import titleTrie
from module.log import logger
from module.task_manager import RUN_TIME_START, TaskNode, TaskQueue
from module.utils import *
from module.web_brows import *

RE_OPEN_MAX = 4  # 异常时最大重新打开次数
SAVE_ERROR_MAX = 2  # 最多保存错误url response次数
RESTART_TIME = -180  # 重新运行
# time
COMPLETE_DELAY = 180  # 默认延迟时间 180分钟
ERROR_DELAY = "10m"  # 网页打开次数过多时延迟时间
NEXT_OPEN_DELAY = (2, 3)  # 默认下次打开的随机时间

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
        nextRunTime = CONFIG.get_task(f"{name}.nextRunTime")
        self.nextRunTime = str2time(nextRunTime) if nextRunTime else \
            str2time(RUN_TIME_START)

    def set_time(self, nextRunTime: datetime):
        self.nextRunTime = nextRunTime
        CONFIG.set_task(f"{self.name}.nextRunTime", str(nextRunTime)[0: 19])


class BidTaskQueue(TaskQueue):
    task: BidTaskState = None

    def __init__(self, run_error=False):
        for name in CONFIG.get_task("TaskList"):
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
    files_path = {
        "list": None,
        "match": None,
        "daymatch": None,
        "daylist": None
    }
    files = {
        "list": None,
        "match": None,
        "daymatch": None,
        "daylist": None
    }
    file_open = False

    def __init__(self, name):
        self.data_file_open()
        self.name = name

    def data_file_init(self):
        for k in self.files_path.keys():
            if "day" in k:  # dayList.txt or dayMatch.txt
                self.files_path[k] = f"{CONFIG.DATA_FOLDER}/bid_{k}_{date_days(format='day')}.txt"
            else:
                self.files_path[k] = f"{CONFIG.DATA_FOLDER}/bid_{k}_{self.name}.txt"

        create_folder(self.files_path["list"])
        log = ""
        for k, v in self.files_path.items():
            log += f"{k}: {v}\n{' '*26}"
        logger.info(log.strip())

    def data_file_open(self):
        if not self.file_open:
            self.data_file_init()
            for k, v in self.files_path.items():
                self.files[k] = open(v, "a", encoding="utf-8")
            # 写入运行时间
            self.file_open = True
            self.write_all(f"{self.name} start at {date_now_s()}\n")
        logger.info(f"{self.name}.file_open={self.file_open}")

    def data_file_exit(self):
        if self.file_open:
            for v in self.files.values():
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

    def _write(self, files, data):
        if not self.file_open:
            self.data_file_open()
        if "\n" in data:
            data = data.replace("\n", "")
        if data[-1] != "\n":
            data = f"{data}\n"
        for k, v in self.files.items():
            if files in k:
                v: TextIOWrapper
                v.write(data)

    def write_all(self, data):
        self.write_match(data)
        self.write_list(data)

    def flush(self):
        if self.file_open:
            for fi in self.files.values():
                fi: TextIOWrapper
                fi.flush()


class Task(DataFileTxt, BidTag, Bid, GetList):
    bid_task: BidTask
    # bid_web: BidHtml
    bid_tag_error = 0
    match_num = 0  # 当次符合条件的项目个数, 仅用于日志打印
    error = False
    bid_task_queue = None

    def __init__(self, name= "", config: dict = None):
        self.name = name
        logger.hr(f"init task {self.name}")
        # for key in ("task", "OpenConfig", "BidTag", "Bid"):
        #     logger.info(f"{key}: {jsdump(config[key])}")
        # config = config["Task"]

        super().__init__(name)
        super(DataFileTxt, self).__init__(config)
        super(BidTag, self).__init__(config)
        super(Bid, self).__init__(config)

        config = config["task"]
        self.next_rule = init_re(config["next_pages"])
        self.error_delay = deep_get(config, "errorDelay") or ERROR_DELAY
        self.complete_delay = deep_get(config, "completeDelay") or COMPLETE_DELAY
        delay = deep_get(config, "nextOpenDelay")
        self.delay = tuple(int(t) for t in delay.split(",")) if delay else NEXT_OPEN_DELAY
        self.bid_task_queue = BidTaskQueue()


    def get_next_pages_url(self, list_url="", next_rule=None, **kwargs) -> str:
        """
        Args:
            list_url (str): 项目列表网址
            next_rule (str): 项目列表网址下一页规则,仅在测试时使用
        Returns:
            next_pages_url (str): 即将打开的url
        """
        next_rule = next_rule or self.next_rule
        if isinstance(next_rule, str):
            next_rule = re.compile(next_rule)
        if not list_url:
            list_url = self.list_url
        pages = str(int(next_rule.search(list_url).group()) + 1)
        next_pages_url = next_rule.sub(pages, list_url)
        logger.info("get next pages url")
        return next_pages_url

    def get_next_list_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            logger.hr("get start url")
            list_url = self.bid_task.return_start_url()
            self.list_url = self.url_extra_params(list_url)
        else:
            self.list_url = self.get_next_pages_url()
        page = self.get_pages()
        logger.info(f"pages: {page}, next_list_url: {self.list_url}")

    def process_next_list_web(self) -> bool:
        """ 打开项目列表页面,获得所有 项目的tag list, 并依次解析tag
        """
        self.match_num = 0  # 开始新网址置为0

        # 下次要打开的项目列表url
        self.get_next_list_url()

        # 打开项目列表页面
        self.html_cut = self.open_and_cut()

        # 解析 html_list_match 源码, 遍历并判断项目列表的项目
        tagList = self.get_tag_list()

        self.process_tag_list(tagList)
        self.flush()  # 刷新缓冲区写入文件

        if not self.match_num:
            logger.info("no match")
        if self.bid_task.state == "complete":
            self._complete_bid_task()
            return False  # state结束
        return True  # state继续

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
            if not self._parse_tag(tag, idx):
                continue

            if self.bid_task.bid_judge(self.bid_info, idx):
                break

            if not self.bid_task.start:  # interrupt状态时判断项目是否开始记录
                self.bid_task.bid_is_start(self.bid_info)
                continue

            if self.tag_filterate():
                self.write_list(f"{self.message()}\n")  # 写入文件
                self._title_trie_search()  # 使用title trie 查找关键词
  
        logger.info(f"tag stop at {idx + 1}, tag counting from 1")
        self.bid_task.set_interrupt(self.bid_info)  # 设置每次最后一个为interrupt
        self.bid_task.set_interrupt_url(self.list_url)
        self.bid_task.print_interrupt()

    def _parse_tag(self, tag: Tag or dict, idx):
        """ 由BidTag.get 读取一个项目项目节点, Bid 接收并对信息进行处理
        Save:
            tag_info(list): 
            bid_info(dict): 
            info_list(list): 
        """
        err_flag = False
        try:
            tag_info = self.get_tag_info(tag)
            # logger.debug(str(infoList))  # 打印每次获得的项目信息
        except Exception:
            err_flag = True
            logger.error(f"tag get error: {tag},\nidx: {idx}, "
                         f"tag rule: {self.tag_key_now}\n"
                         f"{traceback.format_exc()}")
        if not err_flag:
            try:
                self.get_bid_info(*tag_info)
                # logger.debug(self.bid_info)
            except Exception:
                err_flag = True
                logger.error(f"bid receive failed, idx: {idx}, rule: {self.get_bid_now}, "
                             f"{traceback.format_exc()}")
        if err_flag:
            logger.error(f"error idx: {idx}")
            self.bid_tag_error += 1
            if self.bid_tag_error > 5:
                logger.error("too many bid.receive error")
                self.save_response(rps=self.bs, url=self.list_url, save_date=True, extra="parse_tag_error")
                raise ParseTagError
            return False
        return True

    def _title_trie_search(self):
        """ 判断招标标题信息
        """
        result: list = titleTrie.search_all(self.bid_info["name"])
        if result:
            result = f"[{','.join(result)}]; {self.message()}"
            logger.info(result)
            self.write_match(result)
            self.match_num += 1

    def _complete_bid_task(self):
        self.bid_task.set_task("interruptBid.url", "")
        self.list_url = ""

    def _run_bid_task(self):
        while 1:
            result = self.process_next_list_web()
            sleep_random(self.delay, message=" you can use 'Ctrl  C' stop now")
            CONFIG.save()
            if not result:
                break
        logger.info(f"{self.name} {self.bid_task.name} is complete")

    def run_bid_task(self, name) -> datetime:
        self.list_url = None
        self.bid_task = BidTask(name)
        state = CONFIG.get_task(f"{name}.state")
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
            CONFIG.save()
            self.bid_task_queue.insert(bid_task)
        self.close()
        if not self.error:
            reset_task(CONFIG.record, self.name, set_time=True, time=time2str(self.bid_task_queue.head.nextRunTime))
        return self.bid_task_queue.first_runtime(), self.error

    def close(self):
        self.data_file_exit()
        self.request._session.close()


if __name__ == "__main__":

    pass
