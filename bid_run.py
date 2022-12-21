"""
启动任务
读取配置, 初始化运行环境
初始化 任务调度对象，网页浏览对象， 读取配置文件，将配置文件和网页浏览对象交给任务调度对象
任务调度模块
功能为
 打开 .json配置文件
 判断时间，判断访问频率是否合适
 调度网页的打开、项目列表页面的翻页
"""

from time import sleep

from module.log import logger
from module.task import BidTask
from module.utils import *

# 读取配置json
settings_json = "./bid_settings/bid_settings_t.json"
logger.info(f"load json settings file from {settings_json}")


class TaskManager:

    task_name: str = None
    match_list: list = None
    state: str = None
    last_task_state = None

    def __init__(self, json_file, save=True, creat_new=False):
        """ 读取json_file; 设置 settings, json_file , queue
        Args:
            json_file (str):
            save (bool): True: 是否保存到json中
            creat_new (bool): True: 保存到新的配置文件，默认为False
        """
        logger.hr("TaskManager.__init__", 3)
        self.task_dict = {}
        self.settings = read_json(json_file)  # json文件内容
        self.json_file = json_file  # json文件路径
        self.queue = deep_get(self.settings, "task.queue")

        logger.info(f"task queue = {self.queue}")
        if save:  # 当前文件，可选是否保存新副本
            self.json_file = save_json(self.settings, json_file,
                creat_new=creat_new)

    def new_task(self, new_name=""):
        """ 从queue取一个任务名,配置任务,修改管理器的当前任务,修改json_file并保存
        Args:
            new_name (str): 设置新开始的网站任务 必须在task.queue中
        """
        logger.hr("TaskManager.new_task", 3)
        self._set_task_name(new_name)
        deep_set(self.settings, "task.run_time", date_now_s())  # 写入运行时间
        self._build_task()
        save_json(self.settings, self.json_file)

    def _build_task(self):
        logger.info("TaskManager._build_task")
        if self.task_name not in self.task_dict:
            self.task_dict[self.task_name] = \
                BidTask(self.settings[self.task_name], self.task_name)

    def _set_task_name(self, new_name):
        """ 若new_name有值且在queue中,将new_name排到最前面
        # TODO 创建新任务
        Args:
            new_name (str): 要排到最前面的队列
        """
        if new_name and new_name in self.queue:
            idx = self.queue.index(new_name)
            for i in range(idx):
                self.queue.append(self.queue.pop(0))
            logger.info(f"new task start at {new_name}")
        self.task_name = self.queue[0]

    def task_run(self):
        """ 获得任务, 初始化 state
        """
        logger.hr("TaskManager.task_run", 2)
        task: BidTask = self.task_dict[self.task_name]
        if not task.settings["stateQueue"]:
            task.restart()  # TODO
        while task.init_state():  # 若 queue中还有state
            state = ""
            # task执行到所有state完成
            while state != "complete": 
                state = task.process_next_list_web()  # 继续state任务
                save_json(self.settings, self.json_file)
                if state != "complete":
                    sleep_ramdom(
                        message="sleep 3s , you can use 'Ctrl  C' stop now")
                elif state == "open_list_url_error":
                    pass
        logger.info(f"task {self.task_name} is complete")
        return "complete"
        
    def task_complete(self):
        logger.hr("TaskManager.task_complete", 3)
        self.queue.append(self.queue.pop(0))
        deep_set(self.settings, "task.queue", self.queue)
        save_json(self.settings, self.json_file)

        return self.queue[0]

    def exit(self):
        logger.hr("TaskManager.exit")
        save_json(self.settings, self.json_file)
        if self.task_dict:
            for task in self.task_dict.values():
                task.close()


runFlag = True
newFlag = False
fileTest = True

task_continue = 0
web_brows_continue = True
# 初始化任务
bidTaskManager = TaskManager(settings_json,
                             creat_new=(True if newFlag else False))

# TODO
# 写一个死循环,任务调度器不断读取任务队列，进行翻页，读取网页内容
if __name__ == "__main__":
    if runFlag:
        start_name = bidTaskManager.queue[0]
        while task_continue < 1:
            state = ""
            # 判断状态是否开始新任务
            # if bidTaskManager.last_task_state in (None, "complete", ""):
            # 构建新任务
            bidTaskManager.new_task()
            # 任务执行
            try:
                state = bidTaskManager.task_run()
            except KeyboardInterrupt:
                bidTaskManager.exit()
            # 判断执行结果
            if state == "complete":
                # 任务完成
                state = ""
                if start_name == bidTaskManager.task_complete():
                    pass  # 定时30分钟
            
            task_continue += 1

    # bidTaskManager.loop()
    _ = input("enter any key to exit")