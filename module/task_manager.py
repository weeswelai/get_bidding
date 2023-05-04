"""

"""

# import asyncio
import traceback
from datetime import datetime, timedelta

from module import config
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


class TaskNode:
    # 仅保存下次运行时间和任务名
    nextRunTime: datetime = None
    name: str = "test"
    next = None

    def __init__(self, task: str=None) -> None:
        if task:
            self.name = task
            self.nextRunTime = deep_get(config, f"{task}.nextRunTime")
        if not self.nextRunTime:
            self.nextRunTime = RUN_TIME_START
        self.nextRunTime = str2time(self.nextRunTime)
        

class TaskQueue:
    head: TaskNode = None
    len = 0

    def __init__(self) -> None:
        for t in config.taskList:
            self.insert(t)
            self.len += 1

    def insert(self, task):
        if not isinstance(task, TaskNode):
            task = TaskNode(task)

        if self.is_empty():
            self.head = task
            return

        fast = self.head
        idx = 0
        while 1:
            if task.nextRunTime <= fast.nextRunTime:
                # 插在前面
                if idx == 0:
                    self._insert_first(task)
                    break
                slow.next = task
                task.next = fast
                break
                
            if fast.next is None:
                fast.next = task
                break
            else:
                idx += 1
                slow = fast
                fast: TaskNode = fast.next

    def is_empty(self):
        if self.head is None and self.len == 0:
            return True
        return False

    def len_is_one(self):
        if self.len == 1:
            return True
        return False

    def _insert_first(self, task: TaskNode):
        next = self.head
        self.head = task
        task.next = next

    def print(self):
        q = self.head
        while 1:
            logger.info(f"{q.name}: {time2str(q.nextRunTime)}")
            q = q.next
            if q is None:
                break

    def pop(self):
        q = self.head
        self.head = q.next
        q.next = None
        self.len -= 1
        return q

    def first_runtime(self):
        return self.head.nextRunTime


class TaskManager:
    restart = False
    break_ = False
    task: BidTask
    name: str = None
    sleep_now = False

    def __init__(self):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str): 文件json
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件,默认为False
        """
        logger.hr("TaskManager.__init__", 3)
        deep_set(config, "task.run_time", date_now_s())  # 写入运行时间

    # TODO 写得很*, 重写
    def task_run(self):
        """ 完成一个任务
        """
        logger.hr(f"task_run {self.task.name}", 1)
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
        config.save()
        self.task.txt.data_file_exit()
        logger.info(f"task {self.task.name} " f"next run time: {nextRunTime}")
        return nextRunTime

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
            config.save()  # 处理完一页后save
            if result:
                sleep_random(delay_range, message=" you can use 'Ctrl  C' stop now")
            else:
                logger.info(f"{self.task.name} {self.task.url_task} is complete")
                return True

    def web_break(self):
        """判断 break_属性,若为True,抛出WebBreak异常"""
        if self.break_:
            logger.info("web break")
            raise WebBreak

    def exit(self):
        """关闭任务中占用的文件,保存settings"""
        logger.hr("TaskManager.exit")
        config.save()

    def loop(self):
        """ 死循环, 等待、完成 task.list内的任务
        """
        if self.restart:
            self.break_ = self.restart = False

        logger.info(f"task.list: {config['task']['list']}")

        if queue.is_empty():
            logger.info(f"json: task.list is {config.taskList}")
            raise WebBreak
        while 1:
            # 判断 TimerQueue第一个任务是否可执行
            if self.next_task_ready():
                task: TaskNode = queue.pop()    # 第一个任务出队
                self.task = BidTask(config[task.name], task.name)
            else:
                # 阻塞sleep定时
                config.save()
                self.sleep_now = True
                self.sleep(queue.first_runtime())
                continue
            # 任务执行
            self.web_break()
            self.sleep_now = False
            task.nextRunTime = str2time(self.task_run())  # 运行单个任务
            queue.insert(task)  # 将任务插回队列中 
            queue.print()


    def sleep(self, nextRunTime: datetime):
        """阻塞的定时器,阻塞间隔为5秒"""
        
        time_sleep = (nextRunTime - datetime.now()).total_seconds() + 1
        logger.info(f"sleep {time_sleep}")
        interval = 5
        while 1:
            self.web_break()
            if time_sleep > 5:
                sleep(interval)
                time_sleep -= interval
            elif 0 < time_sleep <= 5:
                sleep(time_sleep)
                return
            else:
                return

    def next_task_ready(self) -> None or BidTask:
        """ 若第一个任务时间到了执行时间则返回True
        """
        task: TaskNode = queue.head
        logger.info(f"first task {task.name} nextRunTime: {task.nextRunTime}")
        now = datetime.now().replace(microsecond=0)
        print(time2str(now))
        # 若不处于 当天08时到22时的区间内, 将时间延迟至第二天09点 或当天9点
        nextRunTime = during_runtime(time2str(now))
        if nextRunTime:
            task.nextRunTime = str2time(nextRunTime)
            deep_set(config, f"{task.name}.nextRunTime", nextRunTime)
            logger.info(f"set {task.name} nextRunTime {nextRunTime}")
            queue.insert(queue.pop())
            # queue.print()
            print("False 1")
            return False
        else:
            if task.nextRunTime <= now:
                print("True 1")
                return True
            else:
                print("False 2")
                return False

    def _set_delay_range(self):
        delay_range = self.task.delay if self.task.delay else NEXT_OPEN_DELAY
        return delay_range


bidTaskManager = TaskManager()
queue = TaskQueue()

if __name__ == "__main__":
    try:
        bidTaskManager.loop()
    except Exception:
        bidTaskManager.exit()
        config.save()
