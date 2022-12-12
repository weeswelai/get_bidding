"""
任务调度模块
功能为
 打开 .json配置文件
 判断时间，判断访问频率是否合适
 调度网页的打开、项目列表页面的翻页

"""
from datetime import datetime
from time import sleep
from bs4 import Tag
import traceback
import sys

from module.bid_log import logger
from module.bid_web_brows import web_brows, bid_web, bid_tag, bid
from module.utils import *
from module.bid_judge_content import title_trie


class TaskManager:
    task_name: str
    list_open_url: list = None
    list_url: list  # 当前正则浏览的的项目列表网址
    end_rule: dict  # 翻页结束标志
    state: str
    last_newest: bool  # last.newest是否有值
    bid_list: list or tuple = None
    match_list: list = None

    def __init__(self, json_file, save=True, creat_new=False):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str):
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件，默认为False
        """
        logger.hr("bid_task.init", 3)
        self.settings = read_json(json_file)  # json文件内容
        self.json_file = json_file  # json文件路径
        list_file = deep_get(self.settings, "task.save_data")
        match_file = deep_get(self.settings, "task.match_data")
        creat_folder(list_file)
        self.list_file = open(list_file, "a", encoding="utf-8")
        self.match_list_file = open(match_file, "a", encoding="utf-8")

        logger.info(f"task queue = {deep_get(self.settings, 'task.queue')}")

        if save:  # 当前文件，可选是否保存新副本
            self.json_file = save_json(self.settings, json_file,
                                       creat_new=creat_new)
        self.queue = deep_get(self.settings, "task.queue")

    def build_new_task(self, new_name=""):
        """ 从queue取一个任务名,配置任务,修改管理器的当前任务,修改json_file并保存
        Args:
            new_name (str): 设置新开始的网站任务 必须在task.queue中
        """
        logger.hr("bid_task.build_new_task", 3)
        # 若new_name有值且在queue中,将new_name排到最前面
        self._creat_new_queue(new_name)
        self._get_end_rule()  # 判断任务状态
        deep_set(self.settings, "task.name", self.task_name)
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间
        self.init_brows()

        logger.info(f"url_root: {bid.url_root}")
        deep_set(self.settings, "task.end_rule", self.end_rule)  # 保存 end_rule
        deep_set(self.settings, "task.last_complete", self.state)  # 保存 state
        logger.info(f"build new task {self.task_name} complete")
        save_json(self.settings, self.json_file)
        return self.task_name

    def _creat_new_queue(self, new_name):
        if not new_name and new_name in self.queue:
            idx = self.queue.index(new_name)
            for i in range(idx):
                self.queue.append(self.queue.pop(0))
            logger.info(f"new task start at {new_name}")
        else:
            self.task_name = self.queue[0]

    def init_brows(self):
        settings = self.settings[f"{self.task_name}"]
        web_brows.init(settings)
        bid_tag.init(settings)
        bid.init(settings)

    def build_list_pages_brows(self, list_url_idx=0):
        """
        Args:
            list_url_idx (int): 默认为 0,有的网站会有多个浏览页,需要从列表中取网址
        创建要浏览的页面信息
        """
        logger.hr("bid_task.build_list_pages_brows", 3)
        # TODO 同个网站有多个项目列表页面的情况,如全军采
        if not self.list_open_url:  # 若list_brows_url无实际值, 从json中获得url
            self.list_open_url = deep_get(
                self.settings,
                f"{self.task_name}.url.list")
            self.list_url = self.list_open_url[list_url_idx]
        else:
            self.list_url = web_brows.get_next_pages(self.list_url)
        deep_set(self.settings, f"{self.task_name}.last.taskBreakUrl",
                 self.list_url)
        deep_set(self.settings, "task.web_list.url", self.list_url)
        logger.info(f"list_brows_url: {self.list_open_url}\n" +
                    f"list_url: {self.list_url}")
        save_json(self.settings, self.json_file)

    def get_list_from_list_web_html(self):
        """
        调用web_brows对象对列表网页的源码进行解析，获得项目列表
        若cut_html出错,可能是网络波动,导致网站服务器返回的数据缺失,将重新打开页面
        """
        logger.hr("bid_task.get_list_from_list_web_html", 3)
        # TODO 计算时间 定时 解析网页 解析网页后异常处理 获得列表
        # TODO 列表解析 保存列表
        # 获得list, 包括 url date name b_type
        try:
            tag_list = web_brows.get_bs_tag_list()
        except Exception:
            logger.error(f"\n{traceback.format_exc()}")
            web_brows.save_response(save_date=True, extra="list_Error")
            web_brows.save_response(rps=web_brows.html_list_match,
                                    save_date=True, extra="cut_list_Error")
        self.bid_list = ()
        try:
            for idx, tag in enumerate(tag_list):
                bid.receive(*bid_tag.get(tag))
                if self.state == "break":
                    if not _bid_is_start(bid):
                        logger.info(f"start at {bid.message}")
                        self.process_bid(bid)
                    continue
                elif self.state in (None, "", "complete"):
                    self.process_bid(bid)
                if _bid_is_end(bid, self.end_rule):
                    self._complete_task(bid.message)
        except Exception:
            output = str_list(self.bid_list)[0]
            logger.error(f"{traceback.format_exc()}")
            logger.info(f"error bid list now is \n{output}")
            logger.error(f"error at li_tag[{idx}]\n" +
                         f"error tag: \"{str(tag)}\"")
        self._state()

    def process_bid(self, bid_prj):
        """
        Args:
            bid_prj (bid_web_brows.Bid): 保存 bid 信息的对象
        """
        self.list_file.write(f"{str(bid_prj.message)}\n")
        result = title_trie.search_all(bid_prj.name)
        if result:
            result.append(bid_prj.message)
            self.match_list_file.write(f"{str(result)}\n")
        self.bid_list += (bid_prj.message,)

    def open_list_url(self, reOpen=0):
        """ 打开浏览页面，获得页面招标信息列表
        """
        logger.hr("bid_task.open_list_url", 3)
        if not self.list_url:
            self.list_url = deep_get(self.settings, "task.web_list.list_url")
        web_brows.init_req(url=self.list_url)
        logger.info(f"open {self.list_url}")
        web_brows.open_url_get_response()
        try:  # 在打开网页后立刻判断网页源码是否符合要求
            web_brows.cut_html()  # 必须执行依次cut_html看网站有没有正常获得
        except Exception:
            # TODO 识别出错的网页
            logger.error(f"{traceback.format_exc()}")
            web_brows.save_response(save_date=True, extra="list_Error")
            logger.info(f"cut html error,open {self.list_url} again" + \
                        f"\nreOpen: {reOpen}")
            if reOpen < 3:
                reOpen += 1
                sleep(1.5)  # TODO 换定时器
                self.open_list_url()
            else:
                logger.error(f"{self.list_url} open more than {reOpen} time")
                # TODO 这里需要一个保存额外错误日志以记录当前出错的网址

    def _get_end_rule(self):
        """返回任务的结束规则,根据 self.taskname.last.complete的值返回end_rule
        Return:
            end_rule (dict): 停止条件:
                1. str: 可能为招标项目名或时间
                2. list: 招标项目名和时间的组合
            state (str or None): 上次任务状态
        """
        self.end_rule = {key: "" for key in ["name", "date", "url"]}
        last_task = deep_get(self.settings, f"{self.task_name}.last")
        self.state = deep_get(last_task, "complete")  # 判断该网站上次任务状态
        if self.state in ("", " ", None):  # 既不是break 也不是 complete
            # 以6天为期限算截止条件
            if not last_task["end_rule"]["date"]:
                self.end_rule["date"] = date_days(change_days=-6)
            else:
                self.end_rule = last_task["end_rule"]
        elif self.state == "break":
            self.end_rule = deep_get(last_task, "last.end_rule")
        # 若上次任务已完成,则判断newest
        elif self.state == "complete":
            self.end_rule = deep_get(last_task, "newest")
        else:
            logger.error(f"error complete flag: {self.state}")
            sys.exit(1)
        if len(self.end_rule["date"]) <= 10:
            self.end_rule["date"] = self.end_rule["date"] + " 00:00:00"
        # 上次任务未记录
        self.last_newest = False if last_task["newest"]["name"] == "" else True
        logger.info(f"{self.task_name}.last.complete is: {self.state}")
        logger.info(f"end_rule : {self.end_rule}")

    def _complete_task(self, bid_prj):
        if self.state in ("", " ", None):
            bid_prj = deep_get(self.settings, f"{self.task_name}.last.newest")
        self.state = "complete"
        deep_set(self.settings, f"{self.task_name}.last.complete", "complete")
        deep_set(
            self.settings,
            f"{self.task_name}.last.end_rule",
            _bid_to_dict(bid_prj))
        save_json(self.settings, self.json_file)
        sys.exit()

    def _state(self):
        if self.state in ("", " ", None) and not self.last_newest:  # 任务上次状态未记录
            newest = _bid_to_dict(bid.message)
            newest["date"] = deep_get(self.settings,
                                      "task.run_time")  # 日期改为当前运行时间
            deep_set(self.settings, f"{self.task_name}.last.newest", newest)
            logger.info(f"{self.task_name}.last.newest: {newest}")
        
        # if self.state == "break":
        #     task_break = _bid_list_element_to_dict(web_brows.bid_list, -1)
        #     deep_set(self.settings,
        #              f"{self.task_name}.last.task_break", task_break)
        #     logger.info(f"{self.task_name}.last.task_break: {task_break}")

    def close(self):
        self.list_file.close()
        self.match_list_file.close()

def _date_is_end(date: str, end_date: str, date_len):
    if date_len > 10:
        date_format = "%Y-%m-%d %H:%M:%S"
    elif date_len <= 10:
        date_format = "%Y-%m-%d"
    return datetime.strptime(date, date_format) < \
           datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")


def _bid_is_end(bid, end_rule):
    # TODO 判断日期大小
    is_end = False
    if bid.name == end_rule["name"] or bid.url == end_rule["url"]:
        is_end = True
    if end_rule["date"]:
        if _date_is_end(bid.date, end_rule["date"], len(bid.date)):
            is_end = True
    logger.debug(f"_bid_is_end is {is_end}")
    return is_end


def _bid_is_start(bidPrj, task_break):
    for key in task_break:
        if getattr(bidPrj, key) == task_break[key]:
            return True
    return False


def _bid_list_element_to_dict(bid_list, idx=0):
    return _bid_to_dict(bid_list[idx])


def _bid_to_dict(bid_prj: list):
    if isinstance(bid_prj, list):
        return {
            "name": bid_prj[0],
            "date": bid_prj[1],
            "url": bid_prj[2]
        }
    elif isinstance(bid_prj, dict):
        return bid_prj
    else:
        return {
            "name": "",
            "date": "",
            "url": ""
        }


if __name__ == "__main__":
    json_file_name = r"json\module_1_2022-05-10_17-57-30-559346.json"

    pass
