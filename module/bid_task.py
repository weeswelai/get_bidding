"""
任务调度模块
功能为
 打开 .json配置文件
 判断时间，判断访问频率是否合适
 调度网页的打开、项目列表页面的翻页

"""
import traceback
import sys

from module.bid_log import logger
from module.bid_web_brows import web_brows, bid_web
from module.utils import *
from module.bid_judge_content import title_trie

def _bid_is_end(bid, end_rule):
    # TODO 判断日期大小
    if bid[0] == (end_rule["name"] and bid[3] == end_rule["url"]) \
        or bid[1] == end_rule["date"]:
        return True
    return False

class TaskManager:
    def __init__(self, json_file, save=True, creat_new=False):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str):
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件，默认为False
        """
        logger.hr("bid_task.init", 3)
        self.end_rule = None  # 翻页结束标志
        self.settings = read_json(json_file)  # json文件内容
        self.json_file = json_file  # json文件路径
        # 当前的项目列表网址的列表(同个网站可能有多个项目列表页面)
        self.list_open_url = None   
        self.list_url = None  # 当前正则浏览的的项目列表网址
        self.match_list = []

        if deep_get(self.settings, "task.queue") in [[], [""], ""]:
            deep_set(self.settings, "task.queue",
                     ["zzlh", "hkgy", "jdcg"])  # 默认
        logger.info(f"task queue = {deep_get(self.settings, 'task.queue')}")
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间

        if save:  # 当前文件，可选是否保存新副本
            self.json_file = save_json(self.settings, json_file,
                                       creat_new=creat_new)
        self.queue = deep_get(self.settings, "task.queue")
        self.task_name = self.queue[0]

    def build_new_task(self, new_name=""):
        """ 从queue取一个任务名,配置任务,修改管理器的当前任务,修改json_file并保存
        Args:
            new_name (str): 设置新开始的网站任务 必须在task.queue中
        """
        # 若new_name有值且在queue中,重排queue,将new_name排到最前面
        logger.hr("bid_task.build_new_task", 3)
        if new_name in self.queue:
            idx = self.queue.index(new_name)
            for i in range(idx):
                self.queue.append(self.queue.pop(0))
            logger.info(f"new task start at {new_name}")
        # 取得 task name
        self.task_name = self.queue[0]  # 从queue取第一个元素
        deep_set(self.settings, "task.name", self.task_name)
        # 从settings中获得上次任务相关的配置信息
        self.end_rule, state = self._get_end_rule()

        # 若有cookie 需求(使用第一个cookie)
        if deep_get(self.settings, f"{self.task_name}.url_open_cookie"):
            cookie = _[0]  # 上面的 deep_get 返回一个list
            web_brows.update_req(cookie=cookie)
            bid_web.update_req(cookie=cookie)
        
        web_brows.url_root = deep_get(self.settings, 
                                    f"{self.task_name}.url_open.url_root")
        logger.info(f"url_root: {web_brows.url_root}")
        deep_set(self.settings, "task.end_rule", self.end_rule)  # 保存 end_rule
        deep_set(self.settings, "task.last_complete", state)  # 保存 state
        logger.info(f"build new task {self.task_name} complete")
        save_json(self.settings, self.json_file)
        web_brows.init_rule(
            deep_get(self.settings, f"{self.task_name}.brows_rule")
            )  # 输入浏览列表页面爬取规则

    def build_list_pages_brows(self, list_url_idx=0):
        """
        Args:
            list_url_idx (int): 默认为 0,有的网站会有多个浏览页,需要从列表中取网址
        创建要浏览的页面信息
        """
        logger.hr("bid_task.build_list_pages_brows", 3)
        if not self.list_open_url:  # 若list_brows_url无实际值, 从json中获得url
            self.list_open_url = deep_get(self.settings,
                                          f"{self.task_name}.url_open.list_url")
            self.list_url = self.list_open_url[list_url_idx]
        else:
            # TODO 获得下一页的页面地址
            self.list_url = web_brows.get_next_pages(self.list_url)
        # deep_set(self.settings, f"{self.task_name}.task.web_list.list_url",
        #          self.list_url)
        deep_set(self.settings, "task.web_list.list_url", self.list_url)
        logger.info(f"list_brows_url: {self.list_open_url}\n" +
                    f"list_url: {self.list_url}")
        save_json(self.settings, self.json_file)

    def get_list_from_list_web_html(self):
        """
        调用web_brows对象对列表网页的源码进行解析，获得项目列表
        """
        logger.hr("bid_task.get_list_from_list_web_html", 3)
        # TODO 计算时间 定时 打开网页 打开网页出错后异常处理 解析网页 解析网页后异常处理 获得列表
        # TODO 列表解析 保存列表

        web_brows.cut_html()
        # 获得list, 包括 url date name b_type
        try:
            web_brows.get_list()
        except AttributeError as e:
            output, temp = str_list(web_brows.bid_list)
            logger.info(f"bid list now is {output}")
            logger.error(f"error at li_tag[{web_brows.list_idx}]\n" +
                         f"error tag: \"{web_brows.bs_tag}\"")
            logger.error(f"{traceback.format_exc()}")
            # TODO 出错时同时保存当前时间打开的html源码和match后的源码
            web_brows.save_response()
            # web_brows.save_response(web_brows.html_list_match,
            #                         url=web_brows.url + "match")
        
    def process_bid_list(self):
        """
        """
        logger.hr("bid_task.process_bid_list", 3)
        
        # TODO 遍历列表中的标题，对于标题，招标类型符合条件的(调用判断模块),这里符合条件的是 标题、不为已记录过的，日期大于停止条件的、类型为货物的(暂不判断类型)
        # 遍历列表,找到符合项
        self.match_list = []
        idx_list = []
        task_next = False
        for idx, bid in enumerate(web_brows.bid_list):
            if _bid_is_end(bid, self.end_rule):
                task_next = True
                break
            result = title_trie.search_all(bid[0])
            if result:
                idx_list.append(idx)
                self.match_list.append([bid, result])
        # TODO 将 bid_list存进文件(或数据库中), 从0到idx
        # TODO 将 match_list 存进文件中
        
        logger.info(f"search index:{idx_list}")
        logger.info(f"match_list:\n{str_list(self.match_list)[0].strip()}")
        return task_next



    def save_match_list(self):
        """
        TODO 保存经过前缀树检索后得到的list,保存 bid_list中的信息和match_list的匹配结果
        """
        pass

    # TODO 由self.match_list中的索引找到原 bid_list 拼接招标项目的网址,之后就可以用BidHtml 分析页面
    # def 

    def timer(self):
        """

        Returns:

        """
        pass

    def open_list_url(self):
        """ 打开浏览页面，获得页面招标信息列表
        """
        logger.hr("bid_task.open_list_url", 3)
        if not self.list_url:
            self.list_url = deep_get(self.settings, "task.web_list.list_url")
        web_brows.init_req(url=self.list_url)
        logger.info(f"open {self.list_url}")
        web_brows.open_url_get_response()




    def _get_end_rule(self):
        """返回任务的结束规则,根据 self.last_task.last.complete的值返回end_rule
        Return:
            end_rule (str or list): 停止条件:
                1. str: 可能为招标项目名或时间
                2. list: 招标项目名和时间的组合
            state (str or None): 上次任务状态
        """
        end_rule = {}
        last_task = deep_get(self.settings, f"{self.task_name}.last")
        state = deep_get(last_task, "complete")  # 判断该网站上次任务状态
        if state in ("", " ", None):  # 既不是break 也不是 complete
            # 以6天为期限算截至条件
            end_rule["name"] = ""
            end_rule["url"] = ""
            end_rule["date"] = date_days(change_days=-6)
        elif state == "break":
            end_rule = deep_get(last_task, "last.end_rule")
        elif state == "complete":
            web_list = deep_get(last_task, "web_list")
            end_rule = [web_list["first_name"], web_list["first_date"]]
        else:
            logger.error(f"error complete flag: {state}")
            sys.exit(1)
        logger.info(f"{self.task_name}.last.complete is: {state}")
        logger.info(f"end_rule : {end_rule}")
        return end_rule, state




if __name__ == "__main__":
    json_file_name = r"json\module_1_2022-05-10_17-57-30-559346.json"

    pass
