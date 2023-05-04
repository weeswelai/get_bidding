import os, sys
from shutil import copyfile

# 读取配置json
SETTINGS_DEFAULT = "./bid_settings/bid_settings_default.json"
SETTINGS_JSON = "./bid_settings/bid_settings.json"

CONFIG_DEFAUTL = "./bid_settings/config_default.json"
CONFIG = "./bid_settings/config.json"

if not os.path.exists(SETTINGS_JSON):
    copyfile(SETTINGS_DEFAULT, SETTINGS_JSON)

if not os.path.exists(CONFIG):
    copyfile(CONFIG_DEFAUTL, CONFIG)

pyw_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]  # 入口程序所在的文件,去掉.py和文件夹前缀

IGNORE = ["lineAddLiTag"]
if pyw_name not in IGNORE:        
    from module.log import logger
    from module.utils import read_json, save_json


    class Config(dict):
        def __init__(self) -> None:
            config: dict = read_json("./bid_settings/config.json")
            self.file = config["jsonFIle"]
            d = read_json(self.file)
            for k, v in d.items():
                self[k] = v
            self.taskList = self["task"]["list"]

        def save_json(self):
            save_json(self, self.file)

    config = Config()
    print()