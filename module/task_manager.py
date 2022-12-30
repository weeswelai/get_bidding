"""

"""

import asyncio
import traceback

from module.log import logger
from module.task import BidTask
from module.utils import *

RUN_TIME_START = "2022-01-01 00:00:00"
MIN_DELAY = 30
ERROR_DELAY = 5


class WebBreak(Exception):
    pass


class TaskQueue(list):
    """ 继承list对象,拥有list所有方法,新增自定义方法
    pop_q: 出队一个元素
    insert_task : 将一个任务按下次执行时间插入到队列中
    print_all_next_time : 
    """
    def pop_q(self) -> BidTask:
        if self:
            return self.pop(0)
        else:
            return None

    def insert_task(self, task: BidTask):
        """ 选择插入位置
        """
        if not self:
            self.append(task)
            return None
        for idx, t in enumerate(self):
            if t1_slow_than_t2(t.nextRunTime, task.nextRunTime):
                break
            else:
                continue
        if self.__len__() == 1:
            idx = 1
        self.insert(idx, task)
        return idx

    def print_all_next_time(self):
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
        for key in settings["task"]["list"]:
            task = BidTask(settings[key], key)
            self.set_next_run_time(task)
            self.insert_task(task)
        self.print_all_next_time()

    def set_next_run_time(self, task: BidTask):
        # 判断 "nextRunTime", 若没有值则写入默认起始时间
        if not deep_get(task.settings, "nextRunTime"):
            deep_set(task.settings, "nextRunTime", RUN_TIME_START)
            task.nextRunTime = RUN_TIME_START

    def next_task_ready(self):
        """ 若第一个任务时间到了执行时间,出队该任务
        """
        task: BidTask = self[0]
        logger.info(f"first task {task.task_name} nextRunTime: {task.nextRunTime}")
        if t1_slow_than_t2(date_now_s(), task.nextRunTime):
            return True
        else:
            return False


class TaskManager:
    task_name: str = None
    match_list: list = None
    state: str = None
    last_task_state = None
    restart: bool = False
    break_ = False

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
    def task_run(self, task: BidTask):
        """ 完成一个任务
        """
        logger.hr(f"{task.task_name}.task_run", 1)
        # logger.info(f"run {task.task_name}")
        if not task.settings["stateQueue"]:
            task.restart()
        
        while task.init_state():  # task 按stateQueue顺序完成state
            self.web_break()
            state_result = self.state_run(task)
        min_delay = MIN_DELAY if state_result else ERROR_DELAY
        nextRunTime = get_time_add(min=min_delay)
        deep_set(task.settings, "nextRunTime", nextRunTime)
        task.nextRunTime = nextRunTime
        logger.info(f"task {self.task_name}" f"next run time: {nextRunTime}")

    def state_run(self, task: BidTask):
        """完成一个state"""
        logger.hr(f"{task.task_name}.task_run", 2)
        while 1:
            self.web_break()
            try:
                state_result = task.process_next_list_web()
                self.web_break()
            except AssertionError:  # from task.BidTask._open_list_url
                task.set_error_state()  # 设置state.error为True, 将当前state移动到stateWait
                logger.error(f"{traceback.format_exc()}")
                # TODO 这里需要一个文件保存额外错误日志以记录当前出错的网址, 以及上个成功打开的列表的最后一个项目
                # TODO 一个网址错误次数过多后,将整个任务延迟, 继续下一个state
                logger.warning("open_list_url_error, delay ERROR_DELAY min")
                save_json(self.settings, self.json_file)
                return False
            save_json(self.settings, self.json_file)  # 处理完一页后save
            if state_result:
                sleep_random(message="you can use 'Ctrl  C' stop now")
                # yield True
            else:
                logger.info(f"{task.task_name} {task.state_idx} is complete")
                return True

    def task_complete(self):
        logger.hr("TaskManager.task_complete", 3)
        deep_set(self.settings, "task.queue", self.run_queue)
        save_json(self.settings, self.json_file)
        return self.run_queue[0]

    def web_break(self):
        if self.break_:
            logger.info("web break")
            raise WebBreak

    def exit(self):
        logger.hr("TaskManager.exit")
        save_json(self.settings, self.json_file)
        for task in self.run_queue:
            task: BidTask
            task.close()

    def loop(self):
        """ 死循环, 等待、完成 task.list内的任务
        """
        self.run_queue = RunQueue(self.settings)
        logger.info(f"task.list: {self.settings['task']['list']}")
        if self.restart:
                self.break_ = self.restart = False
                self.settings = read_json(self.json_file)
                
        if not self.run_queue:
            logger.info(f"json: task.list is {self.run_queue}")
            raise WebBreak
        while 1:
            # 判断 TimerQueue第一个任务是否可执行
            if self.run_queue.next_task_ready():
                task = self.run_queue.pop_q()
            else:
                # 阻塞sleep定时
                self.sleep(self.run_queue[0].nextRunTime)
                continue
            # 任务执行
            self.web_break()
            self.task_run(task)
            self.run_queue.insert_task(task)

    def sleep(self, nex_run_tieme: int):
        time_sleep = time_difference_second(nex_run_tieme, date_now_s())
        interval = 5
        self.sleep_now = True
        while 1:
            if time_sleep:
                sleep(interval)
                time_sleep -= interval
            else:
                break

    # async def wait_main(self, wait_time):
    #     time_sleep = time_difference_second(wait_time, date_now_s())
    #     return asyncio.wait([], return_when=asyncio.FIRST_COMPLETED)

    # async def run_main(self, task):
    #     """ coroutine function main
    #     """
    #     return asyncio.wait(
    #         [self.task_run(task),
    #         wait_break()],
    #         return_when=asyncio.FIRST_COMPLETED
    #     )

async def wait_break(self, second=1):
    while 1:
        await asyncio.sleep(second)


def sig_exit(*args):
    loop = asyncio.get_running_loop()
    print("ctrl on signal")
    for task in asyncio.all_tasks():
        task.cancel()
        if task.cancelled:
            print("task is cancelled")
    

async def random_timer(time_range: tuple = (3, 3), message: str = None):
    sleep_time = uniform(*time_range)
    if message:
        print(f"wait {sleep_time} s,{message}")
    logger.info(f"sleep {sleep_time}")
    sleep_idx = int(sleep_time)
    for idx in range(1, sleep_idx + 1):
        print(f"sleep {idx} now")
        await asyncio.sleep(1)  # TODO 后期换成定时器
    if sleep_time - sleep_idx:
        print(f"sleep {sleep_time} now")
        await asyncio.sleep(sleep_time - sleep_idx)
    print("sleep end")



if __name__ == "__main__":
    settings_json = "./bid_settings/bid_settings.json"
    task_manager = TaskManager(settings_json, save=True)
    try:
        task_manager.loop()
    except KeyboardInterrupt:
        task_manager.exit()
