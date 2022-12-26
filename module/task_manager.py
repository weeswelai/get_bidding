from module.log import logger
from module.task import BidTask
from module.utils import *

RUN_TIME_START = "2022-01-01 00:00:00"


class TaskQueue(list):

    def __next__(self):
        if self:
            return self[0]
        else:
            raise StopIteration

    def pop_q(self) -> BidTask:
        if self:
            return self.pop(0)
        else:
            return None

    def insert_q(self, task: BidTask):
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

    def print_q(self):
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
            self.insert_q(task)
        self.print_q()

    def set_next_run_time(self, task: BidTask):
        # 判断 "nextRunTime", 若没有值则写入默认起始时间
        if not deep_get(task.settings, "nextRunTime"):
            deep_set(task.settings, "nextRunTime", RUN_TIME_START)
            task.nextRunTime = RUN_TIME_START

    def next_task_ready(self):
        """ 若第一个任务时间到了执行时间,出队该任务
        """
        nextRunTime = self[0].nextRunTime
        logger.info(f"first task nextRunTime: {nextRunTime}")
        if t1_slow_than_t2(date_now_s(), nextRunTime):
            return True
        else:
            return False


class TaskManager:
    task_name: str = None
    match_list: list = None
    state: str = None
    last_task_state = None
    running: bool = False

    def __init__(self, json_file, save=True, creat_new=False):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str):
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件，默认为False
        """
        logger.hr("TaskManager.__init__", 3)
        self.settings = read_json(json_file)  # 读取json文件
        self.json_file = json_file
        # self.list = deep_get(self.settings, "task.list")
        if save:  # 当前文件，可选是否保存新副本
            self.json_file = save_json(self.settings, json_file,
                                       creat_new=creat_new)
        self.run_queue = RunQueue(self.settings)
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间
        save_json(self.settings, self.json_file)

    # TODO 写得很*, 重写
    def task_run(self, task: BidTask):
        """ 完成一个任务
        TODO 用一个生成器或迭代器, 记录当前process_next_list_web()的位置,然后把控制权交还,交还后的下个event task判断有无退出指令

        """
        logger.hr("TaskManager.task_run", 2)
        logger.info(f"run {task.task_name}")
        min_delay = 30
        if not task.settings["stateQueue"]:
            task.restart()
        while task.init_state():  # task 按stateQueue顺序完成state
            state_result = ""
            # 完成一个state
            while state_result != "complete":
                state_result = task.process_next_list_web()  # 继续state任务
                save_json(self.settings, self.json_file)  # 处理完一页后save
                if state_result != "complete":
                    sleep_ramdom(message="you can use 'Ctrl  C' stop now")
                # TODO 一个网址错误次数过多后,将整个任务延迟, 继续下一个state, 当前state 放入 error list?
                elif state_result == "open_list_url_error":
                    min_delay = 5  # TODO 加几分钟等待时间
                    logger.warning("open_list_url_error, delay 5 min")
                    break
        nextRunTime = get_time_add(min=min_delay)
        deep_set(task.settings, "nextRunTime", nextRunTime)
        logger.info(f"task {self.task_name} is {state_result}, "
                    f"next run time: {nextRunTime}")
        return state_result

    def task_complete(self):
        logger.hr("TaskManager.task_complete", 3)
        deep_set(self.settings, "task.queue", self.run_queue)
        save_json(self.settings, self.json_file)
        return self.run_queue[0]

    def exit(self):
        logger.hr("TaskManager.exit")
        save_json(self.settings, self.json_file)
        for task in self.run_queue:
            task: BidTask
            task.close()

    def loop(self):
        """ 死循环, 等待、完成 RunQueue内的任务
        """
        if not self.run_queue:
            logger.info(f"json: task.list is {self.run_queue}")
            raise KeyboardInterrupt
        while 1:
            # 判断 TimerQueue第一个任务是否可执行
            if not self.running:
                if self.run_queue.next_task_ready():
                    task = self.run_queue.pop_q()
                    self.running = True
                else:
                    logger.info("no task")
                # TODO 将控制权交交还给上一层loop
            # 任务执行
            run_result = self.task_run(task)
            # 判断执行结果
            if run_result:
                pass


if __name__ == "__main__":
    settings_json = "./bid_settings/bid_settings.json"
    task_manager = TaskManager(settings_json, save=False)
