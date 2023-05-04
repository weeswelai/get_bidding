import os, sys
from shutil import copyfile


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
        def __init__(self) -> None:
            config: dict = read_json("./bid_settings/config.json")
            
            self.file = config["jsonFIle"]
            if not os.path.exists(self.file):
                copyfile(SETTINGS_DEFAULT, self.file)

            self.dataFolder = config["testFolder"] \
                if deep_get(config, "test") else config["dataFolder"]
            d = read_json(self.file)
            for k, v in d.items():
                self[k] = v
            self.taskList = self["task"]["list"]

        def save(self):
            save_json(self, self.file)

    config = Config()
    logger.info("config ready")