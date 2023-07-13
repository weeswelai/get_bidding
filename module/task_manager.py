"""
创建任务队列
任务出队
创建任务实例
调用任务运行接口,得到运行结果,根据运行结果决定下次运行时间
任务入队
"""
from datetime import datetime
from importlib import import_module
from os.path import exists

from module.config import config
from module.exception import *
from module.log import logger
from module.utils import *
from module.lineAddLiTag import Writer

RUN_TIME_START = "2023-01-01 00:00:00"  # 默认下次运行时间

class TaskNode:
    # 仅保存下次运行时间和任务名
    nextRunTime: datetime
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
    restart = False

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
            if task.nextRunTime < node.nextRunTime:  # insert before first
                self._insert_first(task)
            else:
                self._insert(task)

    def _insert(self, task:TaskNode):
        node = self.head
        while 1:
            if node.next is None:
                node.next = task
                break
            if  task.nextRunTime < node.next.nextRunTime:
                task.next = node.next
                node.next = task
                break
            else:
                node: TaskNode = node.next

    def is_empty(self):
        if self.head is None:
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
            return
        q = self.head
        while 1:
            logger.info(f"{q.name}: {time2str(q.nextRunTime)}")
            q = q.next
            if q is None:
                break

    def pop(self):
        assert not self.is_empty(), "queue is empty, cannot pop"
        q = self.head
        self.head = q.next
        q.next = None
        return q

    def first_runtime(self):
        if self.is_empty():
            return None
        return self.head.nextRunTime

    def re_insert(self):
        self.insert(self.pop())


class TaskManager(TaskQueue):
    break_ = False
    sleep_now = False

    def __init__(self):
        """
        读取json_file; 设置 settings, json_file , queue

        """
        logger.hr("TaskManager.__init__", 3)
        config.set_("task.run_time", date_now_s())  # 写入运行时间
        super().__init__()

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
        from module.task import Task
        if self.restart:
            queue_restart(self)
        logger.hr("loop start", 0)
        logger.info(f"task.list: {config['task']['list']}")

        if self.is_empty():
            logger.info(f"json: task.list is {config.taskList}")
            raise WebBreak
        while 1:
            if self.next_task_ready():
                taskNode: TaskNode = self.pop()
                task: Task = task_init(taskNode)
            else:
                self.sleep(self.first_runtime())  # 阻塞sleep定时
                logger.set_file_logger()
                continue

            self.web_break()
            taskNode.nextRunTime = task.run()
            config.set_task("nextRunTime", time2str(taskNode.nextRunTime))
            config.save()
            self.insert(taskNode)
            writer = Writer()
            writer.output()

    def sleep(self, nextRunTime: datetime):
        """阻塞的定时器,阻塞间隔为5秒"""
        logger.hr("task manager sleep")
        config.save()
        # self.sleep_now = True
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

    def next_task_ready(self) -> bool:
        """ 若第一个任务时间到了执行时间则返回True
        """
        task: TaskNode = self.head
        logger.info(f"first task {task.name} nextRunTime: {task.nextRunTime}")
        now = datetime.now().replace(microsecond=0)
        # 若不处于 当天08:30到18:00的区间内, 将时间延迟至第二天或当天08点30
        nextRunTime = during_runtime(now)
        if nextRunTime:
            task.nextRunTime = nextRunTime
            deep_set(config, f"{task.name}.nextRunTime", str(nextRunTime))
            logger.info(f"set {task.name} nextRunTime {nextRunTime}")
            self.re_insert()
            return False
        else:
            if task.nextRunTime <= now:
                return True
            else:
                return False


def task_init(task: TaskNode):
    config.name = task.name
    name = task.name
    if exists(f"./module/web/{name}.py"):
        mod = import_module(f"module.web.{name}")
    else:
        mod = import_module(f"module.web.base")
    logger.hr(f"task {name}", 1)
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


def queue_restart(queue: TaskQueue):
    if not queue.restart:
        return
    queue.restart = False
    queue.head = None
    for t in config.taskList:
        config.set_(f"{t}.nextRunTime", RUN_TIME_START)
        TaskList = config.get_(f"{t}.TaskList")
        for bid_task in TaskList:
            config.set_(f"{t}.{bid_task}.nextRunTime", RUN_TIME_START)
        t = TaskNode(t)        
        queue.insert(t)
    queue.print()
    config.save()


if __name__ == "__main__":
    bidTaskManager = TaskManager()
    bidTaskManager.restart = True
    queue_restart(bidTaskManager)
