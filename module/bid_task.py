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




class State:
    settings: dict  # 当前task 的settings 如 zzlh.task1
    newest = False
    start = True  # process_tag_list 中判断

    def __init__(self, settings, state_idx="test") -> None:
        self.state = settings["complete"]
        if self.state == "complete":
            self.state = ""
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
        """
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
        """
        self.state = "complete"
        if deep_get(self.settings, "newest.name") != "":
            deep_set(self.settings, "end_rule", self.settings["newest"])
        deep_set(self.settings, "newest", _bid_to_dict())
        deep_set(self.settings, "interrupt", _bid_to_dict())
        deep_set(self.settings, "interruptUrl", "")
        deep_set(self.settings, "complete", "complete")

    def save_newest_and_interrupt(self, bid: Bid):
        """ 保存最新的招标项目信息, 设置 compelete 为 interrupt
            仅执行一次
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
        """ 三个信息必须全部符合
        Args:
            bid_prj: self.bid
        """
        for key in self.interrupt:
            if getattr(bid_prj, key) == self.interrupt[key] and \
                    self.interrupt[key] != "" :
                continue
            else:
                return None  # 不满足则退出判断
        logger.info("bid is start")
        self.start = True

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


class BidTask:
    settings: dict
    task: dict  # init at _get_next_task
    state_idx: str  # init at _get_next_task
    state: State or InterruptState  # init at _get_state_from_task
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
        self.init_brows(settings)  # input()
        self._creat_save_file()
        # 取一个任务, 若queue 为空报错退出
        # self.init_state(settings)  # 由 TaskManager执行
        
    def init_state(self, settings=None):
        logger.info("bid_task.Bid.init_state")
        if settings is None:
            settings = self.settings
        if self._get_state_idx(deep_get(settings, "task.queue")):
            self._get_state(self.task, self.state_idx)  # 获得当前state
            return True
        return False

    def _creat_save_file(self):
        """ 创建数据保存文件, add 方式
        """
        list_save = f"./data/bid_list_{self.task_name}.txt"
        match_list_save = f"./data/bid_match_list_{self.task_name}.txt"
        creat_folder(list_save)
        self.list_file = open(list_save, "a", encoding="utf-8")
        self.match_list_file = open(match_list_save, "a", encoding="utf-8")

    def _get_state_idx(self, queue: list):
        """ 从queue中取下一个任务赋给 self.task_name(str) 和 self.task(dict),
            若 queue 为空返回False
        """
        if queue:
            self.state_idx = queue[0]
            self.task = deep_get(self.settings, f"{self.state_idx}")
            return True
        else:
            logger.info(f"{self.task_name}.queue is []")
            return False

    def _get_state(self, task: dict, state_idx: str):
        """ 判断当前task, 调用相应的state对象
        Args:
            task (dict): json 中task_name.state 的value
            state_idx (str): json中 task_name.state 的key 
        """
        self.state = InterruptState(task, state_idx) \
            if task["complete"] == "interrupt" else State(task, state_idx)
        logger.info(f"BidTask.state type = \"{task['complete']}\"")
        self.state.print_state()

    def init_brows(self, settings):
        """ 初始化网页对象模型
        """
        self.bid_tag = BidTag(settings)
        self.bid = Bid(settings)
        self.web_brows = WebBrows(settings)
        self.bid_web = BidHtml(settings)
        logger.info(f"url settings: {jsdump(settings['url'])}")
        logger.info(f"rule: {jsdump(settings['rule'])}")

    def _get_ist_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            self.list_url = self.state.return_url()
        else:
            self.list_url = self.web_brows.get_next_pages(self.list_url)

    # def restart(self):
    #     """ 将json中 complete 添加到 queue中
    #     """
    #     logger.inf("bid_task.BidTask.restart")
    #     queue = deep_get(self.settings, "task.queue")
    #     complete = deep_get(self.settings, "task.complete")
    #     queue += complete
    #     deep_set(self.settings, "task.queue", queue)
    #     logger.info(f"queue: {queue}")
    #     self.init_state(self.settings)

    def have_next_state(self):
        if not deep_get(self.settings, "task.queue"):
            return False
        return True

    def complete_task(self):
        """ 将json中 queue 头元素出队,添加到complete中
        """
        queue = deep_get(self.settings, "task.queue")
        complete = deep_get(self.settings, "task.complete")
        complete.append(queue.pop(0))
        deep_set(self.settings, "task.queue", queue)
        deep_set(self.settings, "task.complete", complete)
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
        if self.state.state == "complete":
            self.complete_task()
            return "complete"
        self.state.set_interrupt(self.list_url, self.bid)
        # need save json
        return "continue"

    def process_tag_list(self):
        """ 遍历处理tag_list
        若能遍历到结尾,保存 interruptUrl 和 interrupt
        """
        logger.hr("bid_task.BidTask.process_tag_list", 3)
        # self.bid_list = ()
        for idx, tag in enumerate(self.tag_list):
            try:
                self.bid.receive(*self.bid_tag.get(tag))
                logger.debug(str(self.bid.message))
            except Exception:
                logger.error(f"idx: {idx} tag error: {tag}\n"
                             f"{traceback.format_exc()}")
                continue

            if self.state.bid_is_end(self.bid):
                logger.info("bid is end")
                self.state.complete()  # set self.state.state = "complete"
                break
            if not self.state.newest:
                # 只执行一次,设置state为interrupt, 保存第一个项目信息到 newest
                self.state.save_newest_and_interrupt(self.bid)
            if not self.state.start:
                self.state.bid_is_start(self.bid)
                if not self.state.start:
                    continue
            self.process_bid(self.bid)
        logger.info(f"tag stop at {idx}")

    def process_bid(self, bid_prj: Bid):
        """
        Args:
            bid_prj (bid_web_brows.Bid): 保存 bid 信息的对象
        """
        self.list_file.write(f"{str(bid_prj.message)}\n")
        result: list = title_trie.search_all(bid_prj.name)
        if result:
            logger.info(f"{result} {self.bid.message}")
            result.append(bid_prj.message)
            self.match_list_file.write(f"{str(result)}\n")
        # self.bid_list += (bid_prj.message,)

    def open_list_url(self, url, reOpen=0):
        """ 封装web_brows行为,打开浏览页面，获得裁剪后的页面源码
        """
        logger.hr("bid_task.BidTask.open_list_url", 3)
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


# class TaskManager:

#     name: str
#     list_open: list = None
#     list_url: list  # 当前正在浏览的的项目列表网址
#     bid_list: list or tuple = None
#     match_list: list = None

#     def __init__(self, json_file, save=True, creat_new=False):
#         """ 读取json_file; 设置 settings, json_file , queue
#         Args:
#             json_file (str):
#             save (bool): True: 是否保存到json中
#             creat_new (bool): True: 保存到新的配置文件，默认为False
#         """
#         logger.hr("bid_task.init", 3)
#         self.settings = read_json(json_file)  # json文件内容
#         self.json_file = json_file  # json文件路径
#         list_file = deep_get(self.settings, "task.save_data")
#         match_file = deep_get(self.settings, "task.match_data")
#         creat_folder(list_file)
#         self.list_file = open(list_file, "a", encoding="utf-8")
#         self.match_list_file = open(match_file, "a", encoding="utf-8")

#         logger.info(f"task queue = {deep_get(self.settings, 'task.queue')}")

#         if save:  # 当前文件，可选是否保存新副本
#             self.json_file = save_json(self.settings, json_file,
#                                        creat_new=creat_new)
#         self.queue = deep_get(self.settings, "task.queue")

#     def build_new_task(self, new_name=""):
#         """ 从queue取一个任务名,配置任务,修改管理器的当前任务,修改json_file并保存
#         Args:
#             new_name (str): 设置新开始的网站任务 必须在task.queue中
#         """
#         logger.hr("bid_task.build_new_task", 3)

#         self._creat_new_queue(new_name)
#         self._get_end_rule()  # 判断任务状态

#         deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间

#         logger.info(f"url_root: {bid.url_root}")
#         logger.info(f"build new task {self.name} complete")
#         save_json(self.settings, self.json_file)
#         return self.name

#     def _creat_new_queue(self, new_name):
#         """ 若new_name有值且在queue中,将new_name排到最前面
#         # TODO 创建新任务
#         Args:
#             new_name (str): 要排到最前面的队列
#         """
#         if not new_name and new_name in self.queue:
#             idx = self.queue.index(new_name)
#             for i in range(idx):
#                 self.queue.append(self.queue.pop(0))
#             logger.info(f"new task start at {new_name}")
#         else:
#             self.name = self.queue[0]

#     def build_list_pages_brows(self, list_url_idx=0):
#         """ 创建要浏览的项目列表页面url,或获得下一页的url
#         Args:
#             list_url_idx (int): 默认为0,有的网站会有多个浏览页,需要从列表中取网址
#         """
#         logger.hr("bid_task.build_list_pages_brows", 3)
#         # TODO 同个网站有多个项目列表页面的情况,如全军采
#         if not self.list_open:  # 若list_brows_url无实际值, 从json中获得url
#             self.list_open = deep_get(self.settings, f"{self.name}.url.list")
#             self.list_url = self.list_open[list_url_idx]
#         else:
#             self.list_url = web_brows.get_next_pages(self.list_url)

#         deep_set(self.settings, f"{self.name}.last.taskBreakUrl", self.list_url)
#         deep_set(self.settings, "task.web_list.url", self.list_url)
#         logger.info(f"list_brows_url: {self.list_open}\n" +
#                     f"list_url: {self.list_url}")
#         save_json(self.settings, self.json_file)

#     def get_list_from_list_web_html(self):
#         """
#         # TODO 注释,本段代码太*了，后面再改
#         调用web_brows对象对列表网页的源码进行解析，获得项目列表
#         若cut_html出错,可能是网络波动,导致网站服务器返回的数据缺失,将重新打开页面
#         # TODO 计算时间 定时 解析网页 解析网页后异常处理 获得列表
#         # TODO 列表解析 保存列表
#         """
#         logger.hr("bid_task.get_list_from_list_web_html", 3)
#         task_break = deep_get(self.settings, f"{self.name}.last.interrupt")
#         try:
#             tag_list = web_brows.get_bs_tag_list()
#         except Exception:
#             _except(1)
#         self.bid_list = ()
#         try:
#             for idx, tag in enumerate(tag_list):
#                 bid.receive(*bid_tag.get(tag))
#                 if self.state == "interrupt":
#                     if not _bid_is_start(bid, task_break):
#                         logger.info(f"start at {bid.message}")
#                         deep_set(self.settings, f"{self.name}.taskBreakUrl", 
#                             self.list_url)
#                         if _bid_is_end(bid, self.end_rule):
#                             self._complete_task(bid.message)
#                             return
#                         logger.info(f"set self.state as None")
#                         self.state = None
#                     continue
#                 elif self.state in (None, "", "complete"):
#                     self.process_bid(bid)
#                     deep_set(self.settings, f"{self.name}.state", "interrupt")
#                 if _bid_is_end(bid, self.end_rule):
#                     self._complete_task(bid.message)
#                     return
#                 if idx == 0:
#                     self._state()
#         except Exception:
#             _except(2, self.bid_list, tag)
#         save_json(self.settings, self.json_file)

#     def _get_end_rule(self):
#         """返回任务的结束规则,根据 self.taskname.last.complete的值返回end_rule
#         Return:
#             end_rule (dict): 停止条件:
#                 1. str: 可能为招标项目名或时间
#                 2. list: 招标项目名和时间的组合
#             state (str or None): 上次任务状态
#         """
#         last_task = deep_get(self.settings, f"{self.name}.last")
#         last_state = deep_get(last_task, "complete")  # 判断该网站上次任务状态
#         self.state = "" if last_state == "complete" else last_state

#         self.end_rule = last_task["end_rule"]

#         if not self.end_rule["date"]:
#             self.end_rule["date"] = date_days(change_days=-6)

#         if not last_task["complete"] in ("", " ", None, "interrupt", "complete"):
#             logger.error(f"error complete flag: {self.state}")
#             sys.exit(1)
#         if len(self.end_rule["date"]) <= 10:
#             self.end_rule["date"] = self.end_rule["date"] + " 00:00:00"
#         # 上次任务未记录
#         self.last_newest = False if last_task["newest"]["name"] == "" else True
#         deep_set(self.settings, "f{self.name},state", "interrupt")  # 任务开始
#         logger.info(f"{self.name}.last.complete is: {last_state}\n" +\
#                     f"end_rule : {self.end_rule}")

#     def _complete_task(self, bid_prj):
#         """ 结束任务,保存配置

#         """
#         logger.hr("complete_task", 2)
#         self.state = "complete"
#         last = deep_get(self.settings, f"{self.name}.last")
#         deep_set(last, "complete", "complete")
#         deep_set(last, "end_rule", last["newest"])
#         deep_set(self.settings, f"{self.name}.state", "")
#         save_json(self.settings, self.json_file)

#     def _state(self):
#         if self.state in ("", " ", None, "complete") and \
#             not self.last_newest:  # 任务上次状态未记录
#             newest = _bid_to_dict(bid.message)
#             newest["date"] = deep_get(self.settings,
#                                       "task.run_time")  # 日期改为当前运行时间
#             deep_set(self.settings, f"{self.name}.last.newest", newest)
#             self.last_newest = True
#             logger.info(f"{self.name}.last.newest: {newest}")

#         # if self.state == "interrupt":
#         #     task_break = _bid_list_element_to_dict(web_brows.bid_list, -1)
#         #     deep_set(self.settings,
#         #              f"{self.name}.last.task_break", task_break)
#         #     logger.info(f"{self.name}.last.task_break: {task_break}")

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
        return {
            "name": "",
            "date": "",
            "url": ""
        }


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
        logger.hr("bid_task.init", 3)
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
        logger.hr("bid_task.build_new_task", 3)
        self._return_task_name(new_name)
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间
        self.build_task()
        save_json(self.settings, self.json_file)

    def build_task(self):
        logger.info("bid_task.TaskManager.build_task")
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
        logger.hr("bid_task.task_run", 3)
        task: BidTask = self.task_dict[self.task_name]
        while task.init_state():  # 若 queue中还有state
            state = ""
            while state != "complete": 
                state = task.get_url_list()  # 继续state任务
                save_json(self.settings, self.json_file)
                logger.info("sleep 3s , you can stop now")
                for t in range(1, 4):
                    logger.info(f"sleep {t}s now")
                    sleep(1)  # TODO 后期换成定时器
        logger.info(f"task {self.task_name} is complete")
        return "complete"
        
    def task_complete(self):
        logger.hr("bid_task.task_complete", 3)
        self.queue.append(self.queue.pop(0))
        deep_set(self.settings, "task.queue", self.queue)
        save_json(self.settings, self.json_file)
        return self.queue[0]
