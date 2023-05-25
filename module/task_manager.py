"""
创建任务队列
任务出队
创建任务实例
调用任务运行接口,得到运行结果,根据运行结果决定下次运行时间
任务入队
"""
import traceback
from datetime import datetime
from importlib import import_module
from os.path import exists

from module import config
from module.log import logger
from module.task import BidTask
from module.utils import *
from module.exception import *

RUN_TIME_START = "2022-01-01 00:00:00"  # 默认下次运行时间
COMPLETE_DELAY = 180  # 默认延迟时间 180分钟
ERROR_DELAY = 10  # 网页打开次数过多时延迟时间


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
    head = None
    len = 0

    def __init__(self) -> None:
        for t in config.taskList:
            self.insert(t)
        self.print()

    def insert(self, task) -> None:
        if not isinstance(task, TaskNode):
            task = TaskNode(task)

        node = self.head
        if not node:  # empty queue
            self.head = task
        else:
            if task.nextRunTime <= node.nextRunTime:  # insert before first
                self._insert_first(task)
            else:
                self._insert(task)
        self.len += 1

    def _insert(self, task:TaskNode):
        node = self.head
        while 1:
            if node.next is None:
                node.next = task
                break
            if  task.nextRunTime <= node.next.nextRunTime:
                task.next = node.next
                node.next = task
                break
            else:
                node: TaskNode = node.next

    def is_empty(self):
        if self.head is None and self.len == 0:
            logger.info("queue is empty")
            return True
        return False

    def _insert_first(self, task: TaskNode):
        next = self.head
        self.head = task
        task.next = next

    def print(self):
        if self.is_empty():
            logger.info(f"queue is empty")
        q = self.head
        while 1:
            logger.info(f"{q.name}: {time2str(q.nextRunTime)}")
            q = q.next
            if q is None:
                break

    def pop(self):
        if self.is_empty():
            return None
        q = self.head
        self.head = q.next
        q.next = None
        self.len -= 1
        return q

    def first_runtime(self):
        if self.is_empty():
            return None
        return self.head.nextRunTime

    def re_insert(self):
        self.insert(self.pop())


class TaskManager:
    restart = False
    break_ = False
    task: BidTask
    name: str = None
    sleep_now = False

    def __init__(self):
        """
        读取json_file; 设置 settings, json_file , queue

        """
        logger.hr("TaskManager.__init__", 3)
        self.queue = TaskQueue()
        deep_set(config, "task.run_time", date_now_s())  # 写入运行时间

    # TODO 写得很*, 重写
    def task_run(self, task: BidTask):
        """ 完成一个task中所有的url_task
        """
        logger.hr(f"task_run {task.name}", 1)
        if task.page_list.queue_is_empty():  # 若为空,重新写入PageQueue
            task.page_list.restart()
        task.task_end = False  # pywebio

        if not task.txt.file_open:
            task.txt.data_file_open()

        logger.info(f"task PageQueue: {config.get_task()['PageQueue']}")
        try:
            while task.init_state():  # task 按PageQueue顺序完成state
                self.web_break()
                result = self.url_task_run(task)
        except (WebTooManyVisits, TooManyErrorOpen):
            task.error_open = True
            config.set_task(f"{task.urlTask.name}.error", True)

        # 判断结果 计算下次运行时间, 返回 True 则 延迟 COMPLETE_DELAY , 错误则延迟10分钟或json设置里的时间        
        if task.error_open:
            delay = task.error_delay if task.error_delay \
                else ERROR_DELAY
            logger.warning(f"open_list_url_error, delay {delay}")
        else:
            delay = COMPLETE_DELAY
        nextRunTime = get_time_add(delay=delay)
        deep_set(config, f"{task.name}.nextRunTime", nextRunTime)
        config.save()
        task.close()
        logger.info(f"task {task.name} " f"next run time: {nextRunTime}")
        return nextRunTime

    def url_task_run(self, task: BidTask):
        """完成一个state"""
        logger.hr(f"{task.urlTask.name}.url_task_run", 2)
        while 1:
            self.web_break()
            try:
                result = task.process_next_list_web()
                self.web_break()
            except AssertionError:  # from task.BidTask._open_list_url
                task.set_error_state()  # 设置state.error为True, 将当前state移动到PageWait
                logger.error(f"{traceback.format_exc()}")
                # TODO 这里需要一个文件保存额外错误日志以记录当前出错的网址, 以及上个成功打开的列表的最后一个项目
                return False
            config.save()  # 处理完一页后save
            sleep_random(task.delay, message=" you can use 'Ctrl  C' stop now")
            if not result:
                logger.info(f"{task.name} {task.urlTask.name} is complete")
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

        if self.queue.is_empty():
            logger.info(f"json: task.list is {config.taskList}")
            raise WebBreak
        while 1:
            # 判断第一个任务是否可执行
            if self.next_task_ready():
                taskNode: TaskNode = self.queue.pop()    # 第一个任务出队
                task = task_init(taskNode)
            else:
                # 阻塞sleep定时
                config.save()
                self.sleep_now = True
                self.sleep(self.queue.first_runtime())
                continue
            # 任务执行
            self.web_break()
            self.sleep_now = False
            taskNode.nextRunTime = str2time(self.task_run(task))  # 运行单个任务
            self.queue.insert(taskNode)  # 将任务插回队列中 
            # queue.print()

    def sleep(self, nextRunTime: datetime):
        """阻塞的定时器,阻塞间隔为5秒"""
        
        time_sleep = (nextRunTime - datetime.now()).total_seconds() + 1
        if time_sleep <= 0:
            return
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
        task: TaskNode = self.queue.head
        logger.info(f"first task {task.name} nextRunTime: {task.nextRunTime}")
        now = datetime.now().replace(microsecond=0)
        # 若不处于 当天08:30到18:00的区间内, 将时间延迟至第二天或当天08点30
        nextRunTime = during_runtime(now)
        if nextRunTime:
            task.nextRunTime = nextRunTime
            deep_set(config, f"{task.name}.nextRunTime", str(nextRunTime))
            logger.info(f"set {task.name} nextRunTime {nextRunTime}")
            self.queue.re_insert()
            return False
        else:
            if task.nextRunTime <= now:
                return True
            else:
                return False


def task_init(task: TaskNode) -> BidTask:
    config.name = task.name
    name = task.name
    if exists(f"./module/web/{name}.py"):
        mod = import_module(f"module.web.{name}")
    else:
        mod = import_module(f"module.web.example")
    return mod.Task(name)


def during_runtime(time: datetime) -> datetime or None:
    oneDay = timedelta(days=1)
    today07_30 = datetime.now().replace(hour=7 , minute=30, second=0, microsecond=0)
    today18 = datetime.now().replace(hour=18 , minute=0, second=0, microsecond=0)
    yesterday18 = today18 - oneDay
    tomorrow00 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + oneDay
    if yesterday18 < time < today07_30:
        return today07_30
    elif today18 < time < tomorrow00:
        return today07_30 + oneDay
    return None


bidTaskManager = TaskManager()

if __name__ == "__main__":
    try:
        bidTaskManager.loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        bidTaskManager.exit()
