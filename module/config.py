import json
import os
import sys
from shutil import copyfile

from module.log import logger
from module.utils import (date_now_s, deep_get, deep_set, init_re, jsdump,
                          save_json, cookie_str_to_dict, create_folder)


# file
RECORD_FILE = "./bid_settings/bid_settings.json"
CONFIG_FILE = "./bid_settings/config.json"

pyw_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]  # 入口程序所在的文件,去掉.py和文件夹前缀

# ensure in bid_run.py directory
# if os.getcwd() != sys.path[0] and pyw_name in ("bid_run"):
#     os.chdir(os.path.dirname(sys.argv[0]))
    # print(os.getcwd())

def load_json(file: str) -> dict:
    logger.info(f"load {file}")
    if file in (RECORD_FILE, CONFIG_FILE):
        if not os.path.exists(file):
            logger.warning(f"{file} was not found")
            default = f"{file[:-5]}_default.json"  # [:-5]: get json file name
            copyfile(default, file)
    with open(file, "r", encoding="utf-8") as f:
        return json.loads(f.read())


class Config(object):
    # json key Config
    creatNewJsonFile = False
    run_at_today21 = False
    command: list

    def __init__(self, config=CONFIG_FILE, name="test"):
        self.name = name
        self.data_file = config
        self._config = load_json(config)

        test = self._config["Test"]["Switch"]

        path = self._config["Test"] if test else self._config["File"]
        self.DATA_FOLDER = path["DataFolder"]
        self.record_file = path["JsonFile"]
        self.record = load_json(self.record_file)
        self.taskList = self.record["task"]["list"]

        # json key Config
        for k, v in self.config.items():
            setattr(self, k.lower(), v)
        if self.creatNewJsonFile:
            self.set_new_json()

        logger.info(f"{config} test switch is {test}")

    @property
    def config(self) -> dict:
        return self._config["Config"]

    def set_new_json(self):
        date = date_now_s(file_new=True)
        self.record_file = f"{os.path.splitext(self.record_file)[0]}{date}.json"

    def save(self):
        save_json(self.record, self.record_file, logger=logger)

    def reload(self):
        self = Config()

    def set_task(self, key, data):
        if self.name:
            key = f"{self.name}.{key}" if key else self.name
        self.set_(key, data)

    def get_task(self, key=""):
        if self.name:
            key = f"{self.name}.{key}" if key else self.name
        return self.get_(key)

    def set_(self, key, data):
        deep_set(self.record, key, data)

    def get_(self, key):
        return deep_get(self.record, key)

    @property
    def task(self):
        if not self.name:
            return
        return self.get_task()
    
    @task.setter
    def task(self, task):
        self.name = task


CONFIG = Config()
if os.path.dirname(sys.argv[0])[-3:] == "web":
    if pyw_name != "base":
        CONFIG.task = pyw_name


if __name__ == "__main__":
    pass