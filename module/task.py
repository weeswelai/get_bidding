"""
任务类
包含三个类:
1. State : 表示Task在普通情况下, 上次运行无记录,或上次运行完成
2. InterruptState : 表示Task 上次运行时中断
3. Task : 表示任务, 保存有该任务所必须的规则, 能爬取完一个具体的网站
"""
import traceback
from datetime import datetime
from time import sleep

from bs4 import Tag

from module.judge_content import title_trie
from module.log import logger
from module.web_brows import *
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
    list_file = None
    match_list_file = None
    list_url: str = None
    bid_tag_error = 0

    def __init__(self, settings, task_name="test") -> None:
        self.settings = settings  # zzlh:{}
        self.task_name = task_name  # 当前任务名
        self.match_num = 0  # 当次符合条件的项目个数, 仅用于日志打印
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
        self.list_file.write(f"start at {date_now_s()}\n")
        self.match_list_file.write(f"start at {date_now_s()}\n")

    def close(self):
        self.list_file.close()
        self.match_list_file.close()

    def _get_state_idx(self, queue: list):
        """ 从stateQueue中取第一个state 赋给 self.state_idx(str)
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

    def init_state(self):
        """ 用_get_state_idx 判断 task.stateQueue 中是否还有state
        有则用 _init_state 初始化State 并返回 True,
        无则返回 False
        
        Returns:
            (bool): 初始化完成返回 True ,失败返回 False 
        """
        logger.info("BidTask.init_state")
        # 若queue中还有state
        if self._get_state_idx(deep_get(self.settings, "stateQueue")):
            self._init_State(self.state_idx)
            return True
        return False

    def restart(self):
        """ 将json中 complete 添加到 queue中
        """
        logger.info("BidTask.restart")
        queue = deep_get(self.settings, "stateQueue")
        complete = deep_get(self.settings, "stateComplete")
        queue += complete
        deep_set(self.settings, "stateComplete", [])
        logger.info(f"queue: {queue}")

    def process_next_list_web(self):
        """ 打开项目列表页面,获得所有 项目的tag list, 并依次解析tag
        """
        logger.info("BidTask.get_url_list")
        self.match_num = 0  # 开始新网址置为0
        
        # 下次要打开的项目列表url
        self._get_next_list_url()
        
        # 打开项目列表页面, 获得 self.web_brows.html_list_match
        try:
            self._open_list_url(self.list_url)
        except AssertionError:
            logger(f"{self.list_url} open more than {reOpen} time")
            # TODO 这里需要一个保存额外错误日志以记录当前出错的网址, 以及上个成功打开的列表的最后一个项目
            return "open_list_url_error"
        
        # 解析 html_list_match 源码, 遍历并判断项目列表的项目
        self.tag_list = self.web_brows.get_bs_tag_list()
        self._process_tag_list()  

        if self.match_num:
            logger.info("no match")
        if self.State.state == "complete":
            self._complete_state()
            return "complete"
        return "continue"

    def _get_next_list_url(self):
        """ 获得下次打开的 url 保存在self.list_url
        """
        if not self.list_url:
            self.list_url = self.State.return_url()
        else:
            self.list_url = self.web_brows.get_next_pages(self.list_url)

    def _open_list_url(self, url, reOpen=0):
        """ 封装web_brows行为,打开浏览页面，获得裁剪后的页面源码
        """
        logger.hr("BidTask._open_list_url", 3)
        try:  # 在打开网页后立刻判断网页源码是否符合要求
            self.web_brows.open(url=url)
            self.web_brows.cut_html()
        except Exception:
            # TODO 识别出错的网页
            logger.error(f"{traceback.format_exc()}")
            self.web_brows.save_response(save_date=True, extra="list_Error")
            logger.info(f"cut html error,open {self.list_url} again"
                        f"\nreOpen: {reOpen}")
            if reOpen < 3:
                reOpen += 1
                sleep(2)  # TODO 换定时器
                self._open_list_url(url, reOpen)
            assert reOpen < 3 , "a"

    def _process_tag_list(self):
        """ 遍历处理 self.tag_list
        若能遍历到结尾,保存 interruptUrl 和 interrupt
        """
        logger.hr("BidTask.process_tag_list", 3)
        for idx, tag in enumerate(self.tag_list):
            try:
                self.bid.receive(*self.bid_tag.get(tag))
                # logger.debug(str(self.bid.message))  # 打印每次获得的项目信息
            except Exception:
                logger.error(f"idx: {idx} tag error: {tag}, "
                            f"rule: {self.bid_tag.get_now}\n"
                            f"{traceback.format_exc()}")
                self.bid_tag_error += 1
                if self.bid_tag_error > 10:
                    logger.error("too many bid.receive error")
                    raise KeyboardInterrupt
                continue

            if self.State.bid_is_end(self.bid):  # 判断是否符合结束条件
                self.State.complete()  # set self.State.state = "complete"
                break
            if not self.State.newest:  # 只执行一次
                self.State.save_newest_and_interrupt(self.bid)
            if not self.State.start:
                if not self.State.bid_is_start(self.bid):
                    continue
            self.State.set_interrupt(self.list_url, self.bid)
            
            self.list_file.write(f"{str(self.bid.message)}\n")
            self._title_trie_search(self.bid)
        logger.info(f"tag stop at {idx}")

    def _title_trie_search(self, bid_prj: Bid):
        """ 处理 bid对象

        Args:
            bid_prj (bid_web_brows.Bid): 保存 bid 信息的对象
        """
        result: list = title_trie.search_all(bid_prj.name)
        if result:
            logger.info(f"{result} {self.bid.message}")
            result.append(bid_prj.message)
            self.match_list_file.write(f"{str(result)}\n")
            self.match_num += 1

    def _complete_state(self):
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


if __name__ == "__main__":
    json_file = "./bid_settings/bid_settings_t.json"
    json_set = read_json(json_file)
    bid_task_name = "zzlh"
    bid_task_test = BidTask(json_set[bid_task_name])
    
    # test code
    try:
        bid_task_test.restart()
    # use Ctrl + C exit
    except KeyboardInterrupt:
        pass
    save_json(json_set, json_file)
