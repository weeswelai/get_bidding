import os, sys
from json import loads
from shutil import copyfile

from module.utils import deep_set

# 读取配置json
SETTINGS_DEFAULT = "./bid_settings/bid_settings_default.json"

CONFIG_DEFAULT = "./bid_settings/config_default.json"
CONFIG_FILE = "./bid_settings/config.json"

if not os.path.exists(CONFIG_FILE):
    copyfile(CONFIG_DEFAULT, CONFIG_FILE)

with open(CONFIG_FILE, "r", encoding="utf-8") as c_json:
    CONFIG = loads(c_json.read())
    TEST = True if CONFIG["test"]["switch"] else False

pyw_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]  # 入口程序所在的文件,去掉.py和文件夹前缀

IGNORE = ["lineAddLiTag"]
if pyw_name not in IGNORE:
    from module.utils import save_json, deep_get


    class Config(dict):
        name = ""

        def __init__(self) -> None:
            c = CONFIG["test"] if TEST else CONFIG["file"]
            self.dataFolder = c["dataFolder"]
            self.file = c["jsonFIle"]
            if not os.path.exists(self.file):
                copyfile(SETTINGS_DEFAULT, self.file)
            with open(self.file, "r", encoding="utf-8") as f:
                d = loads(f.read())
            for k, v in d.items():
                self[k] = v
            self.taskList = self["task"]["list"]

        def save(self):
            save_json(self, self.file)

        def reload(self):
            self = Config()

        def set_task(self, key, data):
            self.set_(f"{self.name}.{key}", data)

        def get_task(self, key=""):
            if key:
                return self.get_(f"{self.name}.{key}")
            return self[self.name]

        def set_(self, key, data):
            deep_set(self, key, data)

        def get_(self, key):
            return deep_get(self, key)


    config = Config()
    if os.path.dirname(sys.argv[0])[-3:] == "web":
        if pyw_name != "base":
            config.name = pyw_name
