import os, sys
from shutil import copyfile

from module.utils import deep_set


# 读取配置json
SETTINGS_DEFAULT = "./bid_settings/bid_settings_default.json"

CONFIG_DEFAUTL = "./bid_settings/config_default.json"
CONFIG = "./bid_settings/config.json"

if not os.path.exists(CONFIG):
    copyfile(CONFIG_DEFAUTL, CONFIG)

pyw_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]  # 入口程序所在的文件,去掉.py和文件夹前缀

IGNORE = ["lineAddLiTag"]
if pyw_name not in IGNORE:        
    from module.log import logger
    from module.utils import read_json, save_json, deep_get

    class Config(dict):
        name = ""
        def __init__(self) -> None:
            config: dict = read_json("./bid_settings/config.json")
            c = config["test"] if config["test"]["switch"] else config["file"]
            self.dataFolder = c["dataFolder"]
            self.file = c["jsonFIle"]
            if not os.path.exists(self.file):
                copyfile(SETTINGS_DEFAULT, self.file)
            d = read_json(self.file)
            for k, v in d.items():
                self[k] = v
            self.taskList = self["task"]["list"]

        def save(self):
            save_json(self, self.file)

        def read(self):
            self = Config()

        def set_task(self, key, data):
            self._set(f"{self.name}.{key}", data)

        def get_task(self, key=""):
            if key:
                return self._get(f"{self.name}.{key}")
            return self[self.name]

        def _set(self, key, data):
            deep_set(self, key, data)

        def _get(self, key):
            return deep_get(self, key)


    config = Config()
    if os.path.dirname(sys.argv[0])[-3:] == "web":
        if pyw_name == "example":
            pyw_name = input("please input task name")
        config.name = pyw_name
    logger.info(f"config ready, name={config.name}")