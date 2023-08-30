import json
import os
import sys
from shutil import copyfile

from module.log import logger
from module.utils import cookie_str_to_dict, deep_set, init_re, jsdump

# time
COMPLETE_DELAY = 180  # 默认延迟时间 180分钟
ERROR_DELAY = "10m"  # 网页打开次数过多时延迟时间
NEXT_OPEN_DELAY = (2, 3)  # 默认下次打开的随机时间

# file
SETTINGS_DEFAULT = "./bid_settings/bid_settings_default.json"
CONFIG_DEFAULT = "./bid_settings/config_default.json"
CONFIG_FILE = "./bid_settings/config.json"

pyw_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]  # 入口程序所在的文件,去掉.py和文件夹前缀

# ensure in bid_run.py directory
if os.getcwd() != sys.path[0] and pyw_name in ("bid_run"):
    os.chdir(os.path.dirname(sys.argv[0]))
    # print(os.getcwd())

# ensure have config.json
if not os.path.exists(CONFIG_FILE):
    copyfile(CONFIG_DEFAULT, CONFIG_FILE)

with open(CONFIG_FILE, "r", encoding="utf-8") as c_json:
    CONFIG = json.loads(c_json.read())
    TEST = True if CONFIG["test"]["switch"] else False
    logger.info(f"{CONFIG_FILE} test switch is {TEST}")

IGNORE = ("lineAddLiTag")
if pyw_name not in IGNORE:
    from module.utils import deep_get, save_json

    class Config(dict):
        name = ""
        creatNewJsonFile = False
        run_at_today18 = False

        def __init__(self) -> None:
            self.command = []
            path = CONFIG["test"] if TEST else CONFIG["file"]
            self.dataFolder = path["dataFolder"]
            self.file: str = path["jsonFIle"]
            if not os.path.exists(self.file):
                copyfile(SETTINGS_DEFAULT, self.file)
            with open(self.file, "r", encoding="utf-8") as f:
                settings = json.loads(f.read())
            for k, v in settings.items():
                self[k] = v
            self.taskList = self["task"]["list"]
            for k, v in CONFIG["config"].items():
                setattr(self, k, v)
            if self.creatNewJsonFile:
                self.set_new_json()

        def set_new_json(self):
            from os.path import splitext

            from module.utils import date_now_s
            date = date_now_s(file_new=True)
            self.file = f"{splitext(self.file)[0]}{date}.json"

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


HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }


class TaskBaseConfig:
    name = ""
    # GetList
    list_url = ""
    method = "GET"  # 默认
    headers: dict = None
    cookies: dict = None
    time_out = 16
    delay: tuple = (2, 3)
    next_pages: str = ""
    encoding = "utf-8"
    html_cut_rule = None  # regular expression or re.compile(html_cut_rule)
    html_cut: str = ""  # html_cut = cut_html()
    bs = None   # Tag or dict
    li_tag = None  # TODO rename ListTag to li_tag
    tag_list: list = None
    # BidTag
    tag_rules: dict = None
    # Bid
    bid_cut: dict = None
    url_root: dict = None
    # Task
    next_rule = None # regular expression
    error_delay: str
    complete_delay: str
    delay: tuple


class TaskConfig(TaskBaseConfig):
    def __init__(self, name="", settings: dict=None) -> None:
        self.name = name if name else config.name
        settings = settings if settings else config.get_task()
        logger.hr(f"init task {self.name}")
        for key in ("task", "OpenConfig", "BidTag", "Bid"):
            logger.info(f"{key}: {jsdump(settings[key])}")
        self.get_url_init(settings["OpenConfig"])
        self.tag_rules = settings["BidTag"]  # BidTag init
        self.bid_init(settings["Bid"])
        self.bid_task_init(settings["task"])

    def get_url_init(self, openConfig: dict=None):
        """
        读 settings.json 获得method, delay, headers和cookies
        """
        for k, v in openConfig.items():
            if k == "cookies":
                if isinstance(v, str):
                    v = cookie_str_to_dict(v)
            if k == "html_cut":
                self.html_cut_rule = init_re(v)
                continue
            setattr(self, k, v)
        if "User-Agent" not in self.headers or not self.headers:
            self.headers["User-Agent"] = HEADERS["User-Agent"]
    
    def bid_init(self, settings=None):
        self.bid_cut = {}
        rule = settings["re"]
        for k, v in rule.items():
            self.bid_cut[k] = init_re(v)
            logger.debug(f"rule init {k}: {self.bid_cut[k]}")
        self.url_root = settings["urlRoot"]

    def bid_task_init(self, settings=None):
        self.next_rule = init_re(settings["next_pages"])
        self.error_delay = deep_get(settings, "errorDelay") or ERROR_DELAY
        self.complete_delay = deep_get(settings, "completeDelay") or COMPLETE_DELAY
        delay = deep_get(settings, "nextOpenDelay")
        self.delay = tuple(int(t) for t in delay.split(",")) if delay else NEXT_OPEN_DELAY
