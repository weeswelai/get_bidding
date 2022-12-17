"""
任务调度模块
功能为
 打开 .json配置文件
 判断时间，判断访问频率是否合适
 调度网页的打开、项目列表页面的翻页
# TODO 将 state task 拆成两个对象

"""
import sys
import traceback
from datetime import datetime
from time import sleep

from bs4 import Tag

from module.bid_judge_content import title_trie
from module.bid_log import logger
from module.bid_web_brows import *
from module.utils import *

data_path = r"./data"


class State:
    settings: dict  # 当前task 的settings 如 zzlh.task1
    newest = False
    start = True  # process_tag_list 中判断
    state = ""  # 默认为 ""

    def __init__(self, settings, state_idx="test") -> None:
        self.state = settings["complete"]
        self.end_rule = settings["end_rule"]  # 翻页结束标志
        self.list_url = settings["url"]
        self.state_idx = state_idx
        self.settings = settings
        self.init_end_rule()

    def init_end_rule(self):
        """ 判断 end_rule 是否合法
        """
        if not self.end_rule["date"]:
            self.end_rule["date"] = date_days(change_days=-6)
        if len(self.end_rule["date"]) <= 10:
            self.end_rule["date"] = self.end_rule["date"] + " 00:00:00"
        logger.info(f"json: {self.state_idx}.complete = \"{self.state}\"\n"
                    f"end_rule : {self.end_rule}")

    def bid_is_end(self, bid_prj: Bid):
        """ 判断当前项目是否符合结束条件
        Args:
            bid_prj (<class> Bid): 当前Bid对象, 保存项目信息
        """
        if bid_prj.name == self.end_rule["name"] \
                and bid_prj.url == self.end_rule["url"]:
            return True
        if self.end_rule["date"]:
            if _date_is_end(bid_prj.date, self.end_rule["date"],
                            len(bid_prj.date)):
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
        if deep_get(self.settings, "newest.name") != "":
            deep_set(self.settings, "end_rule", self.settings["newest"])
        deep_set(self.settings, "newest", _bid_to_dict())
        deep_set(self.settings, "interrupt", _bid_to_dict())
        deep_set(self.settings, "interruptUrl", "")
        deep_set(self.settings, "complete", "complete")

    def save_newest_and_interrupt(self, bid: Bid):
        """ 保存最新的招标项目信息, 设置 compelete 为 interrupt
            仅执行一次, interrupt状态下不执行
        """
        bid_message = _bid_to_dict(bid)
        if len(bid_message["date"]) < 10:
            bid_message["date"] = date_now_s()
        deep_set(self.settings, "newest", bid_message)
        deep_set(self.settings, "complete", "interrupt")  # 启动后状态设为interrupt
        self.newest = True

    def set_interrupt(self, list_url, bid):
        """ 保存遍历完成时的 list_url 和最新的 bid 到 interrupt设置
        interrupt状态下在 self.start==True后保存
        其他状态self.start默认为True
        """
        if self.start:
            deep_set(self.settings, "interruptUrl", list_url)
            deep_set(self.settings, "interrupt", _bid_to_dict(bid))

    def return_url(self):
        if self.settings["url"]:
            return self.settings["url"]
        else:
            logger.error(f"{self.state_idx}.url: is empty, "
                         "please check settings json file")
            exit()

    def print_state(self):
        logger.info(f"state = {self.state}, newest = {self.newest}, "
                    f"start = {self.start}\n")
        if self.state == "interrupt":
            logger.info(f"interruptUrl = {self.settings['interruptUrl']}\n"
                        f"interrupt = {jsdump(self.settings['interrupt'])}")


class InterruptState(State):
    state = "interrupt"

    def __init__(self, settings, state_idx="test") -> None:
        super().__init__(settings, state_idx)
        self.interrupt = self.settings["interrupt"]
        self.newest = True
        self.start = False
        
        if deep_get(self.settings, "interrupt.name") == "":
            logger.error(f"{self.state_idx}.interrupt.name is empty, "
                         "please check settings json file")
            exit()

    def bid_is_start(self, bid_prj: Bid):
        """判断条件为: name, date, url 三个信息必须全部符合, 符合返回True 并
        将 InterruptState.state 置为 True, 不符合 返回 False .
        仅在 interrupt状态下判断输入项目是否符合条件,
        json中state.interrupt 信息为自动生成, 若手动填写请注意是否填写正确,否则
        可能导致一直到符合 end_rule 并结束state 时都没有符合开始条件
        
        Args:
            bid_prj: self.bid
        """
        for key in self.interrupt:  # name, date, url
            if getattr(bid_prj, key) == self.interrupt[key] \
                and self.interrupt[key] != "" :
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

    def return_url(self):
        if self.settings["interruptUrl"]:
            return self.settings["interruptUrl"]
        else:
            logger.error(f"{self.state_idx}.interruptUrl: is empty, "
                         "please check settings json file")
            exit()

# TODO 初始化和 State 初始化, 以及 state重新初始化
class BidTask:
    settings: dict  # 初始化新的State时用到
    state_idx: str  # init at _get_state  "state1" or "state2"
    State: InterruptState  # 也有可能是State类 init at _get_state_from_task
    bid: Bid
    bid_tag: BidTag
    web_brows: WebBrows
    bid_web: BidHtml
    tag_list = None  # 源码解析后的 list
    bid_list: list
    list_file = None
    match_list_file = None
    list_url: str = None

    def __init__(self, settings, task_name="test") -> None:
        self.settings = settings  # zzlh:{}
        self.task_name = task_name  # 当前任务名
        logger.info(f"init task {self.task_name}")
        self._init_brows(settings)
        self._creat_save_file()

    def _init_brows(self, settings):
        """ 初始化网页对象模型, 只在初始化时调用一次
        
        Args:
            settings (dict): json中 的具体任务
        """
        self.bid_tag = BidTag(settings)
        self.bid = Bid(settings)
        self.web_brows = WebBrows(settings)
        self.bid_web = BidHtml(settings)
        logger.info(f"url settings:\n{jsdump(settings['url'])}\n"
                    f"rule:\n{jsdump(settings['rule'])}")

    def _creat_save_file(self):
        """ 创建数据保存文件, add 方式
        """
        list_save = f"{data_path}/bid_list_{self.task_name}.txt"
        match_list_save = f"{data_path}/bid_match_list_{self.task_name}.txt"
        creat_folder(list_save)
        self.list_file = open(list_save, "a", encoding="utf-8")
        self.match_list_file = open(match_list_save, "a", encoding="utf-8")
        # 写入一行运行时间
        self.list_file.write(date_now_s())
        self.match_list_file.write(date_now_s())

    def _get_state_idx(self, queue: list):
        """ 从queue中取第一个state 赋给 self.state_idx(str)
        若 queue 为空返回False
        """
        if queue:
            self.state_idx = queue[0]
            logger.info(f"BidTask._get_state_idx = {self.state_idx}")
            return True
        else:
            logger.info(f"{self.task_name}.queue is []")
            return False

    def _init_State(self, state_idx: str):
        """ 判断state_idx中的 complete, 初始化相应的State对象

        Args:
            state_idx (str): json中 task_name.state 的key, 例如 state1
        """
        setting = self.settings[state_idx]
        self.State = InterruptState(setting, state_idx) \
            if setting["complete"] == "interrupt" else State(setting, state_idx)
        logger.info(f"json: {self.task_name}{self.state_idx}.state= "
                    f"\"{setting['complete']}\"")
        self.State.print_state()

    def init_state(self, settings=None):
        """ 若 task.stateQueue 中还有state, 初始化State
        
        Returns:
            (bool): 初始化完成返回 True ,失败返回 False 
        """
        logger.info("BidTask.init_state")
        # 若queue中还有state
        if self._get_state_idx(deep_get(self.settings, "stateQueue")):
            self._init_State(self.state_idx)
            return True
        return False

    def _get_ist_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            self.list_url = self.State.return_url()
        else:
            self.list_url = self.web_brows.get_next_pages(self.list_url)

    def restart(self):
        """ 将json中 complete 添加到 queue中
        """
        logger.inf("BidTask.restart")
        queue = deep_get(self.settings, "stateQueue")
        complete = deep_get(self.settings, "stateComplete")
        queue += complete
        deep_set(self.settings, "stateQueue", queue)
        logger.info(f"queue: {queue}")
        self.init_state(self.settings)

    def have_next_state(self):
        if not deep_get(self.settings, "stateQueue"):
            return False
        return True

    def complete_task(self):
        """ 将json中 queue 头元素出队,添加到complete中
        """
        queue = deep_get(self.settings, "stateQueue")
        complete = deep_get(self.settings, "stateComplete")
        complete.append(queue.pop(0))
        deep_set(self.settings, "stateQueue", queue)
        deep_set(self.settings, "stateComplete", complete)
        logger.info(f"{self.state_idx} complete, queue: {queue}\n"
                    f"complete: {complete}")
        if queue:
            self.state_idx = queue[0]

    def get_url_list(self):
        """ 打开项目列表页面,获得所有 项目的tag list, 并依次解析tag
        """
        logger.info("BidTask.get_url_list")
        self._get_ist_url()
        # 打开项目列表页面, 获得 self.web_brows.html_list_match
        self.open_list_url(self.list_url)
        # 解析 html_list_match 源码
        self.tag_list = self.web_brows.get_bs_tag_list()
        self.process_tag_list()
        if self.State.state == "complete":
            self.complete_task()
            return "complete"
        # need save json
        return "continue"

    def process_tag_list(self):
        """ 遍历处理tag_list
        若能遍历到结尾,保存 interruptUrl 和 interrupt
        """
        logger.hr("BidTask.process_tag_list", 3)
        for idx, tag in enumerate(self.tag_list):
            try:
                self.bid.receive(*self.bid_tag.get(tag))
                # logger.debug(str(self.bid.message))  # 打印每次获得的项目信息
            except Exception:
                logger.error(f"idx: {idx} tag error: {tag}\n"
                             f"{traceback.format_exc()}")
                continue

            if self.State.bid_is_end(self.bid):
                self.State.complete()  # set self.State.state = "complete"
                break
            if not self.State.newest:
                # 只执行一次,设置state为interrupt, 保存第一个项目信息到 newest
                self.State.save_newest_and_interrupt(self.bid)
            if not self.State.start:
                if not self.State.bid_is_start(self.bid):
                    continue

            self.State.set_interrupt(self.list_url, self.bid)
            self.list_file.write(f"{str(self.bid.message)}\n")
            self.title_trie_search(self.bid)
        logger.info(f"tag stop at {idx}")

    def title_trie_search(self, bid_prj: Bid):
        """ 处理 bid对象

        Args:
            bid_prj (bid_web_brows.Bid): 保存 bid 信息的对象
        """
        result: list = title_trie.search_all(bid_prj.name)
        if result:
            logger.info(f"{result} {self.bid.message}")
            result.append(bid_prj.message)
            self.match_list_file.write(f"{str(result)}\n")

    def open_list_url(self, url, reOpen=0):
        """ 封装web_brows行为,打开浏览页面，获得裁剪后的页面源码
        """
        logger.hr("BidTask.open_list_url", 3)
        try:  # 在打开网页后立刻判断网页源码是否符合要求
            self.web_brows.open(url=url)
            self.web_brows.cut_html()
        except Exception:
            # TODO 识别出错的网页,
            logger.error(f"{traceback.format_exc()}")
            self.web_brows.save_response(save_date=True, extra="list_Error")
            logger.info(f"cut html error,open {self.list_url} again"
                        f"\nreOpen: {reOpen}")
            if reOpen < 3:
                reOpen += 1
                sleep(2)  # TODO 换定时器
                self.open_list_url(url, reOpen)
            else:
                logger.error(f"{self.list_url} open more than {reOpen} time")
                self.web_brows.save_response(save_date=True, extra="list_Error")
                # TODO 这里需要一个保存额外错误日志以记录当前出错的网址, 以及上个成功打开的列表的最后一个项目

    def close(self):
        self.list_file.close()
        self.match_list_file.close()

def _date_is_end(date: str, end_date: str, date_len):
    if date_len > 10:
        date_format = "%Y-%m-%d %H:%M:%S"

    elif date_len <= 10:
        date_format = "%Y-%m-%d"
        end_date = end_date[:10]
    return datetime.strptime(date, date_format) < \
        datetime.strptime(end_date, date_format)


def _bid_list_element_to_dict(bid_list, idx=0):
    return _bid_to_dict(bid_list[idx])


def _bid_to_dict(bid_prj=None):
    if isinstance(bid_prj, list):
        return {
            "name": bid_prj[0],
            "date": bid_prj[1],
            "url": bid_prj[2]
        }
    elif isinstance(bid_prj, dict):
        return bid_prj
    elif isinstance(bid_prj, Bid):
        return {
            "name": bid_prj.name,
            "date": bid_prj.date,
            "url": bid_prj.url
        }
    else:
        return {key: "" for key in ("name", "date", "url")}


class TaskManager:

    task_name: str = None
    match_list: list = None
    state: str = None

    def __init__(self, json_file, save=True, creat_new=False):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str):
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件，默认为False
        """
        logger.hr("TaskManager.__init__", 3)
        self.task_dict = {}
        self.settings = read_json(json_file)  # json文件内容
        self.json_file = json_file  # json文件路径
        self.queue = deep_get(self.settings, "task.queue")

        logger.info(f"task queue = {self.queue}")
        if save:  # 当前文件，可选是否保存新副本
            self.json_file = save_json(self.settings, json_file,
                creat_new=creat_new)

    def new_task(self, new_name=""):
        """ 从queue取一个任务名,配置任务,修改管理器的当前任务,修改json_file并保存
        Args:
            new_name (str): 设置新开始的网站任务 必须在task.queue中
        """
        logger.hr("TaskManager.new_task", 3)
        self._return_task_name(new_name)
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间
        self._build_task()
        save_json(self.settings, self.json_file)

    def _build_task(self):
        logger.info("TaskManager._build_task")
        if self.task_name not in self.task_dict:
            self.task_dict[self.task_name] = \
                BidTask(self.settings[self.task_name], self.task_name)

    def _return_task_name(self, new_name):
        """ 若new_name有值且在queue中,将new_name排到最前面
        # TODO 创建新任务
        Args:
            new_name (str): 要排到最前面的队列
        """
        if not new_name and new_name in self.queue:
            idx = self.queue.index(new_name)
            for i in range(idx):
                self.queue.append(self.queue.pop(0))
            logger.info(f"new task start at {new_name}")
        else:
            if self.task_name:
                self.queue.append(self.queue.pop(0))
                deep_set(self.settings, "task.queue", self.queue)
            else:
                self.task_name = self.queue[0]

    def task_run(self):
        """ 获得任务, 初始化 state
        """
        logger.hr("TaskManager.task_run", 3)
        task: BidTask = self.task_dict[self.task_name]
        if task.settings["stateQueue"] == []:
            task.restart()  # TODO
        while task.init_state():  # 若 queue中还有state
            state = ""
            while state != "complete": 
                state = task.get_url_list()  # 继续state任务
                save_json(self.settings, self.json_file)
                print("sleep 3s , you can stop now")
                if state != "complete":
                    for t in range(1, 4):
                        print(f"sleep {t}s now")
                        sleep(1)  # TODO 后期换成定时器
        logger.info(f"task {self.task_name} is complete")
        return "complete"
        
    def task_complete(self):
        logger.hr("TaskManager.task_complete", 3)
        self.queue.append(self.queue.pop(0))
        deep_set(self.settings, "task.queue", self.queue)
        save_json(self.settings, self.json_file)
        return self.queue[0]
