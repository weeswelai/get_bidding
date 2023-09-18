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

from module.config import CONFIG
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
        self.error = False
        if task:
            self.name = task
            self.nextRunTime = deep_get(CONFIG.record, f"{task}.nextRunTime")
        if not self.nextRunTime:
            self.nextRunTime = RUN_TIME_START
        self.nextRunTime = str2time(self.nextRunTime)


class TaskQueue:
    head = None

    def __init__(self) -> None:
        for t in CONFIG.taskList:
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

    def __init__(self, restart=False):
        """
        读取json_file; 设置 settings, json_file , queue

        """
        logger.hr("TaskManager.__init__", 3)
        CONFIG.set_("task.run_time", date_now_s())  # 写入运行时间
        import_web_module()
        super().__init__()
        if restart:
            queue_restart(self)

    # def web_break(self):
    #     """判断 break_属性,若为True,抛出WebBreak异常"""
    #     if self.break_:
    #         logger.info("web break")
    #         raise WebBreak

    def exit(self):
        """关闭任务中占用的文件,保存settings"""
        logger.hr("TaskManager.exit")
        CONFIG.save()

    def loop(self):
        """ 死循环, 等待、完成 task.list内的任务
        """
        from module.task import Task
        logger.hr("loop start", 0)
        logger.info(f"task.list: {CONFIG.record['task']['list']}")

        if self.is_empty():
            logger.info(f"json: task.list is {CONFIG.taskList}")
            raise WebBreak
        while 1:
            if self.next_task_ready():
                taskNode: TaskNode = self.pop()
                task: Task = task_init(taskNode)
            else:
                self.sleep(self.first_runtime())  # 阻塞sleep定时
                logger.set_file_logger()
                continue

            # self.web_break()
            taskNode.nextRunTime, taskNode.error = task.run()
            taskNode.nextRunTime, reset_time = compare_nextRunTime(self, taskNode)
            if reset_time:
                reset_task(CONFIG.record, taskNode.name, time=time2str(taskNode.nextRunTime))
            else:
                CONFIG.set_task("nextRunTime", time2str(taskNode.nextRunTime))

            CONFIG.save()
            self.insert(taskNode)
            writer = Writer(argv=CONFIG.command)
            writer.output()

    def sleep(self, nextRunTime: datetime):
        """阻塞的定时器,阻塞间隔为5秒"""
        logger.hr("task manager sleep")
        CONFIG.save()
        # self.sleep_now = True
        time_sleep = (nextRunTime - datetime.now()).total_seconds() + 1
        if time_sleep <= 0:
            return
        logger.info(f"sleep {time_sleep}")
        interval = 5
        while 1:
            # self.web_break()
            if time_sleep > 5:
                time.sleep(interval)
                time_sleep -= interval
            elif 0 < time_sleep <= 5:
                time.sleep(time_sleep)
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
            deep_set(CONFIG, f"{task.name}.nextRunTime", str(nextRunTime))
            logger.info(f"set {task.name} nextRunTime {nextRunTime}")
            self.re_insert()
            return False
        else:
            if task.nextRunTime <= now:
                return True
            else:
                return False


def task_init(task: TaskNode):
    CONFIG.task = task.name
    name = task.name
    if exists(f"./module/web/{name}.py"):
        mod = import_module(f"module.web.{name}")
    else:
        from module.task import Task
        return Task(name, CONFIG.task)
    logger.hr(f"task {name}", 1)
    return getattr(mod, name.title())(name, CONFIG.task)


def during_runtime(time: datetime) -> datetime or None:
    ONEDAY = timedelta(days=1)
    today07_30 = datetime.now().replace(hour=7 , minute=30, second=0, microsecond=0)
    today21 = datetime.now().replace(hour=21 , minute=0, second=0, microsecond=0)
    yesterday21 = today21 - ONEDAY
    tomorrow00 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + ONEDAY
    if CONFIG.run_at_today21:
        today21 = time
    if yesterday21 < time < today07_30:
        return today07_30
    elif today21 < time < tomorrow00:
        return today07_30 + ONEDAY
    return None


def queue_restart(queue: TaskQueue):
    logger.hr("task restart", 3)
    queue.head = None
    for t in CONFIG.taskList:
        CONFIG.set_(f"{t}.nextRunTime", RUN_TIME_START)
        TaskList = CONFIG.get_(f"{t}.TaskList")
        for bid_task in TaskList:
            CONFIG.set_(f"{t}.{bid_task}.nextRunTime", RUN_TIME_START)
        t = TaskNode(t)        
        queue.insert(t)
    queue.print()
    CONFIG.save()


def import_web_module():
    from os import listdir
    for module in listdir("./module/web"):
        if module.endswith(".py"):
            import_module(f"module.web.{module[:-3]}")


def compare_nextRunTime(queue: TaskQueue, task_insert: TaskNode):
    reset_time = True
    if task_insert.error:
        reset_time = False
        return task_insert.nextRunTime, reset_time
    task = queue.head
    while task:
        if (task_insert.nextRunTime - task.nextRunTime).seconds <= 3600:  # 1小时内
            if task.error:
                task = task.next
                continue
            return task.nextRunTime, reset_time
        task = task.next
    return task_insert.nextRunTime, reset_time


if __name__ == "__main__":
    bidTaskManager = TaskManager()
    # bidTaskManager.restart = True
    # queue_restart(bidTaskManager)
    bidTaskManager.loop()
