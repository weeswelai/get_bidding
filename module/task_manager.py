"""

"""
import traceback
from datetime import datetime

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
    head = None
    len = 0

    def __init__(self) -> None:
        for t in config.taskList:
            self.insert(t)

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
    def task_run(self, task: BidTask):
        """ 完成一个任务
        """
        logger.hr(f"task_run {task.name}", 1)
        delay_range = task.delay if task.delay else NEXT_OPEN_DELAY  # 移到task.py
        if task.page_list.queue_is_empty():  # 若为空,重新写入PageQueue
            task.page_list.restart()
        task.task_end = False

        if not task.txt.file_open:
            task.txt.data_file_open()

        logger.info(f"task PageQueue: {task.settings['PageQueue']}")
        try:
            result = True
            while task.init_state():  # task 按PageQueue顺序完成state
                self.web_break()
                result = self.url_task_run(task, delay_range)
        except WebTooManyVisits:
            result = False
            deep_set(task.settings, f"{task.url_task}.error", True)

        # 判断结果 计算下次运行时间, 返回 True 则 延迟 COMPLETE_DELAY , 错误则延迟10分钟或json设置里的时间        
        if result:
            delay = COMPLETE_DELAY
        else:
            delay = task.error_delay if task.error_delay \
                else ERROR_DELAY
            logger.warning(f"open_list_url_error, delay {delay}")
        nextRunTime = get_time_add(delay=delay)
        # 设置下次运行时间
        deep_set(task.settings, "nextRunTime", nextRunTime)
        config.save()
        task.txt.data_file_exit()
        logger.info(f"task {task.name} " f"next run time: {nextRunTime}")
        return nextRunTime

    def url_task_run(self, task: BidTask, delay_range):
        """完成一个state"""
        logger.hr(f"{task.url_task}.url_task_run", 2)
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
            if result:
                sleep_random(delay_range, message=" you can use 'Ctrl  C' stop now")
            else:
                logger.info(f"{task.name} {task.url_task} is complete")
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
            # 判断第一个任务是否可执行
            if self.next_task_ready():
                taskNode: TaskNode = queue.pop()    # 第一个任务出队
                task = BidTask(config[taskNode.name], taskNode.name)
            else:
                # 阻塞sleep定时
                config.save()
                self.sleep_now = True
                self.sleep(queue.first_runtime())
                continue
            # 任务执行
            self.web_break()
            self.sleep_now = False
            taskNode.nextRunTime = str2time(self.task_run(task))  # 运行单个任务
            queue.insert(taskNode)  # 将任务插回队列中 
            queue.print()


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
        task: TaskNode = queue.head
        logger.info(f"first task {task.name} nextRunTime: {task.nextRunTime}")
        now = datetime.now().replace(microsecond=0)
        # 若不处于 当天08时到22时的区间内, 将时间延迟至第二天09点 或当天9点
        nextRunTime = during_runtime(now)
        if nextRunTime:
            task.nextRunTime = nextRunTime
            deep_set(config, f"{task.name}.nextRunTime", str(nextRunTime))
            logger.info(f"set {task.name} nextRunTime {nextRunTime}")
            queue.insert(queue.pop())
            return False
        else:
            if task.nextRunTime <= now:
                return True
            else:
                return False


bidTaskManager = TaskManager()
queue = TaskQueue()

if __name__ == "__main__":
    try:
        bidTaskManager.loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        bidTaskManager.exit()
