"""

"""

# import asyncio
import traceback

from module.log import logger
from module.task import BidTask
from module.utils import *
from module.web_exception import WebTooManyVisits

RUN_TIME_START = "2022-01-01 00:00:00"  # 默认下次运行时间
COMPLETE_DELAY = 180  # 默认延迟时间 180分钟
ERROR_DELAY = 10  # 网页打开次数过多时延迟时间
NEXT_OPEN_DELAY = (2, 3)  # 默认下次打开的随机时间

# webio点击stop按钮时引发的异常
class WebBreak(Exception):
    pass


class TaskQueue(list):
    """ 继承list对象,拥有list所有方法,新增自定义方法
    pop_q: 出队一个元素
    insert_task : 将一个已初始化好的任务按下次执行时间插入到队列中
    print_all_next_time : 
    """
    def pop_q(self) -> BidTask:
        """出队第一个元素"""
        if self:
            return self.pop(0)
        else:
            return None

    def insert_task(self, task: BidTask):
        """ 将已初始化好的任务插入队列中,按nexRunTime排序
        """
        queue_iter = iter(self)
        try:
            idx = 0
            while 1:
                t: BidTask = next(queue_iter)
                if t1_slow_than_t2(t.nextRunTime, task.nextRunTime):
                    break
                else:
                    idx += 1
        # 到底了
        except StopIteration:
            idx = self.__len__()
        self.insert(idx, task)
        return idx

    def print_all_next_time(self):
        """依次输出队列下次运行时间"""
        log = ""
        if self:
            for t in self:
                t: BidTask
                log = f"{log}{t.task_name}.nextRunTime: {t.nextRunTime}\n"
        logger.info(log.strip())


class RunQueue(TaskQueue):
    def __init__(self, settings) -> None:
        """ 运行队列
        
        Args:
            settings (dict): 整个json文件的信息
        """
        # for key in settings:
        #     if key in ("task", "default"):
        #         continue
        # self.task_set = set()
        for key in settings["task"]["list"]:
            # 初始化任务并加入队列
            task = BidTask(settings[key], key)
            self.set_next_run_time(task)
            self.insert_task(task)
        self.print_all_next_time()
        self.print_queue()

    def set_next_run_time(self, task: BidTask):
        # 判断 "nextRunTime", 若没有值则写入默认起始时间
        if not deep_get(task.settings, "nextRunTime"):
            deep_set(task.settings, "nextRunTime", RUN_TIME_START)
            task.nextRunTime = RUN_TIME_START

    def next_task_ready(self) -> bool:
        """ 若第一个任务时间到了执行时间则返回True
        """
        task: BidTask = self[0]
        logger.info(f"first task {task.task_name} nextRunTime: {task.nextRunTime}")
        sleep(1.1)  # 防止两个时间秒数相等
        if t1_slow_than_t2(date_now_s(), task.nextRunTime):
            return True
        else:
            return False
    
    def print_queue(self):
        """输出当前list里所有任务名"""
        task_queue = []
        for task in self:
            task_queue.append(task.task_name)
        logger.info(f"queue: {task_queue}")


class TaskManager:
    match_list: list = None  
    restart: bool = False
    break_ = False
    task: BidTask
    run_queue: RunQueue
    sleep_now = False

    def __init__(self, json_file, save=True, creat_new=False):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str):
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件,默认为False
        """
        logger.hr("TaskManager.__init__", 3)
        self.settings = read_json(json_file)  # 读取json文件
        self.json_file = json_file
        # self.list = deep_get(self.settings, "task.list")
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间
        if save:  # 当前文件，可选是否保存新副本
            self.json_file = save_json(self.settings, json_file,
                                       creat_new=creat_new)

    # TODO 写得很*, 重写
    def task_run(self):
        """ 完成一个任务
        """
        logger.hr(f"{self.task.task_name}.task_run", 1)
        delay_range = self.task.delay if self.task.delay else NEXT_OPEN_DELAY
        if self.task.page_list.queue_is_empty():  # 若为空,重新写入PageQueue
            self.task.page_list.restart()
        self.task.task_end = False
        if not self.task.txt.file_open:
            self.task.txt.data_file_open()
        logger.info(f"task PageQueue: {self.task.settings['PageQueue']}")
        try:
            result = True
            while self.task.init_state():  # task 按PageQueue顺序完成state
                self.web_break()
                result = self.url_task_run(delay_range)
        except WebTooManyVisits:
            result = False
            deep_set(self.task.settings, f"{self.task.url_task}.error", True)

        # 判断结果 计算下次运行时间, 返回 True 则 延迟 COMPLETE_DELAY , 错误则延迟10分钟或json设置里的时间        
        if result:
            delay = COMPLETE_DELAY
        else:
            delay = self.task.error_delay if self.task.error_delay \
                else ERROR_DELAY
            logger.warning(f"open_list_url_error, delay {delay}")
        nextRunTime = get_time_add(delay=delay)
        # 设置下次运行时间
        deep_set(self.task.settings, "nextRunTime", nextRunTime)
        self.task.nextRunTime = nextRunTime
        save_json(self.settings, self.json_file)
        self.task.txt.data_file_exit()
        logger.info(f"task {self.task.task_name}" f"next run time: {nextRunTime}")

    def url_task_run(self, delay_range):
        """完成一个state"""
        logger.hr(f"{self.task.url_task}.url_task_run", 2)
        while 1:
            self.web_break()
            try:
                result = self.task.process_next_list_web()
                self.web_break()
            except AssertionError:  # from task.BidTask._open_list_url
                self.task.set_error_state()  # 设置state.error为True, 将当前state移动到PageWait
                logger.error(f"{traceback.format_exc()}")
                # TODO 这里需要一个文件保存额外错误日志以记录当前出错的网址, 以及上个成功打开的列表的最后一个项目
                return False
            save_json(self.settings, self.json_file)  # 处理完一页后save
            if result:
                sleep_random(delay_range, message=" you can use 'Ctrl  C' stop now")
            else:
                logger.info(f"{self.task.task_name} {self.task.url_task} is complete")
                return True

    def web_break(self):
        """判断 break_属性,若为True,抛出WebBreak异常"""
        if self.break_:
            logger.info("web break")
            raise WebBreak

    def exit(self):
        """关闭任务中占用的文件,保存settings"""
        logger.hr("TaskManager.exit")
        save_json(self.settings, self.json_file)
        if hasattr(self, "run_queue"):
            for task in self.run_queue:
                task: BidTask
                task.txt.data_file_exit()

    def loop(self):
        """ 死循环, 等待、完成 task.list内的任务
        """
        if self.restart:
            self.break_ = self.restart = False
            self.settings = read_json(self.json_file)
        logger.info(f"task.list: {self.settings['task']['list']}")
        self.run_queue = RunQueue(self.settings)

        if not self.run_queue:
            logger.info(f"json: task.list is {self.run_queue}")
            raise WebBreak
        while 1:
            # 判断 TimerQueue第一个任务是否可执行
            if self.run_queue.next_task_ready():
                self.task = self.run_queue.pop_q()
            else:
                # 阻塞sleep定时
                self.sleep_now = True
                self.sleep(self.run_queue[0].nextRunTime)
                continue
            # 任务执行
            self.web_break()
            self.sleep_now = False
            self.task_run()  # 运行单个任务
            self.run_queue.insert_task(self.task)  # 将任务插入队列中
            self.run_queue.print_all_next_time()

    def sleep(self, nex_run_tieme: int):
        """阻塞的定时器,阻塞间隔为5秒"""
        if t1_slow_than_t2(date_now_s(), nex_run_tieme):
            return None
        time_sleep = time_difference_second(nex_run_tieme, date_now_s())
        logger.debug(f"sleep {time_sleep}")
        interval = 5
        while 1:
            self.web_break()
            if time_sleep > 0:
                sleep(interval)
                time_sleep -= interval
            else:
                return None


if __name__ == "__main__":
    settings_json = "./bid_settings/bid_settings.json"
    task_manager = TaskManager(settings_json, save=True)
    try:
        task_manager.loop()
    except Exception:
        task_manager.exit()
        save_json(settings_json, task_manager.settings)
