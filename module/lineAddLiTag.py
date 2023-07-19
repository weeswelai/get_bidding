"""
命令行输入规则
0. 默认开启-d -h -e 
1. -d : 指定时间 格式为 mm-dd, 若 -d 后不输入时间,则默认为当天
2. -h : 输出htm文件
3. -e : 输出excel文件
4. -i : dayFile 需要指定 输入类型, 可选输入(小写L)  l m mn
        mn 为 match文件, 不输出已匹配关键词

暂定
-t : 选择txt文件输出, 需要指定txt文件
-p : 选择网站输出

调用接口:
调用Writer和Command
"""

import sys
from json import loads
from os.path import exists, basename

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from module.config import CONFIG_FILE
from module.utils import date_days

DATAPATH = "./data"
MATCH = "bid_match"
LIST = "bid_list"

INDEX = 0
TITLE = -4
DATE = -3
URL = -2
TYPE = -1

# "jdcg", "zzlh", "hkgy", "zhzb", "qjc", "cebpub"
WEB = ["jdcg", "zzlh", "hkgy", "zhzb", "qjc", "cebpub"]

date_time = ""

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config =  loads(f.read())
    TEST = True if config["test"]["switch"] else False
    DATAFOLDER = config["test"]["dataFolder"] if TEST else config["file"]["dataFolder"]


class Command:
    day: str = None
    excel = None
    htm = None
    List = None
    Match = None
    match_no_keyword = None
    argv = None
    _argv = None

    def __init__(self, argv: list = None) -> None:
        if argv:
            if argv[0].endswith(".py"):
                del(argv[0])
        if not argv:
            for k in ("excel", "htm", "List", "Match"):
                setattr(self, k, True)
            self.day = date_days(format="day")
            return
        self.argv = argv.copy()
        self._argv = argv.copy()  # save command
        while self.argv:
            # print(f"argv: {self.argv}")
            command = self.argv.pop(0)
            if command == "-d":
                self.command_day()
            elif command == "-e":
                self.excel = True
            elif command == "-h":
                self.htm = True
            elif command == "-i":
                self.command_file_in()
            else:
                self.error(command)
        if self.excel is None and self.htm is None:
            self.excel = self.htm = True
        if self.List is None and self.Match is None:
            self.List = self.Match = True
        if self.day is None:
            self.day = date_days(format="day")

    def command_day(self):
        self.day = date_days(format="day")
        if not self.argv or self.argv[0].startswith("-"):
            return
        else:
            command = self.argv.pop(0)
            date = command.split("-")
            for d in date:
                if not d.isdigit():
                    self.error(command)
            if len(command) == 5:  # mm-dd -> yyyy-mm-dd
                command = f"{self.day[:4]}-{command}"
            self.day = command

    def command_file_in(self):
        if not self.argv or self.argv[0].startswith("-"):
            self.List = self.Match = True
            return
        for _ in range(0, 2):
            if not self.argv or self.argv[0].startswith("-"):
                return
            command = self.argv.pop(0)
            if command == "l":
                self.List = True
            elif command == "m":
                self.Match = True
            elif command == "mn":
                self.Match = True
                self.match_no_keyword = True
            else:
                self.error(command)

    def error(self, command):
        print(f"command input error: {command}")
        exit()


class Htm:
    def __init__(self) -> None:
        self.name: str = None
        self.output = None
        self.time = None
        self.line = None  # fun
        self.idx = 1

    def init(self, name: str, type, match_no_keyword):
        self.name = name[:-4] + ".htm"
        self.output = open(self.name, "w", encoding="utf-8")
        self.line = self.list
        if type == "match" and not match_no_keyword:
            self.line = self.match

    def head(self, *args):
        # html <head>标签, 显示标题
        self.output.write(f"""<head>
        <title>{self.name.split(".")[0]}</title>
    </head>\n""")

    def body(self, body):
        if body == "top":
            self.output.write(f'<body onload=scrollToBottom(); style="background-color: #C7EDCC">\n')
            self.function()
        elif body == "bottom":
            for _ in range(0,8):
                self.output.write("<li></li>\n")
            self.output.write("</body>")

    def function(self):
        # 页面渲染完成后自动滚到底部
        self.output.write("""
        <script>
            // 页面渲染完成后自动滚到底部
            function scrollToBottom()
            {
                window.scrollTo(0, document.getElementsByTagName("body")[0].scrollHeight);
            }
        </script>
        """)

    def labels_a(self, title, url):
        return f"<a href=\"{url}\">{title}</a>"

    def li(self, line: str):
        if ";" in line:
            line = get_list(line)
            labelsA = self.labels_a(line[TITLE], line[URL])
            data = self.line(line, labelsA, self.idx)
            self.output.write(data)
            self.idx += 1
        else:
            self.output.write(f"<li>{line.strip()}</li>\n")

    def list(self, line, labelsA, idx):
        return f"<li>{str(idx)}. {labelsA}, {line[DATE]}</li>\n"

    # match 一行会分为5个 [匹配关键词]; 标题; 日期; url; 类型
    def match(self, line, labelsA, idx):
        return f"<li>{str(idx)}. {line[0]}: {labelsA}, {line[DATE]}</li>\n"

    def exit(self):
        self.output.close()


class Excel:
    def __init__(self) -> None:
        self.name = None  # 保存的文件
        self.line = None  # fun
        self.workbook: Workbook = None
        self.sheet: Worksheet = None
        self.type = None
        self.title_idx: list = None
        self.row = 2
        self.idx = 1

    def init(self, name: str, type, match_no_keyword):
        self.type = type
        self.row = 2
        name = basename(name)[:-4]
        self.name = name + ".xlsx"
        idx = 1
        # 若excel已打开,则在扩展名之前加上(序号)
        while exists(f"{DATAFOLDER}/~${self.name}"):
            self.name = f"{name}({idx}).xlsx"
            idx += 1
        self.name = f"{DATAFOLDER}/{self.name}"
        # 初始化工作表
        self.workbook = Workbook()
        self.sheet = self.workbook.active  # 第一张工作表
        # 需要写入的列
        self.title_idx = ["A", "B", "C", "D"]
        if self.type == "match" and not match_no_keyword:
            self.title_idx.append("E")

    def head(self, *args, **kwargs):
        title = ["序号", "标题", "日期", "URL"]
        width = [6, 95, 20, 10]  # 列宽
        if self.type == "match":
            title.insert(1, "匹配词")
            width.insert(1, 20)
        # 写入标题
        for i, col in enumerate(self.title_idx):
            self.sheet[f"{col}1"] = title[i]
            col = col[0]
            self.sheet.column_dimensions[col].width = width[i]
        del(self.title_idx[0])  # 序号列单独写入
        # 冻结窗格 B2
        self.sheet.freeze_panes = "B2"

    def body(self, body):
        if body == "bottom":
            if self.type == "match":
                self.sheet.auto_filter.ref = "B1:C1"
            else:
                self.sheet.auto_filter.ref = "B1"

    def li(self, line, *args):
        if ";" not in line:
            self.sheet[f"B{self.row}"] = line
        else:
            line_list = get_list(line)
            self.sheet[f"A{self.row}"] = self.idx
            for i, col in enumerate(self.title_idx):
                self.sheet[f"{col}{self.row}"] = line_list[i]
            self.idx += 1
        self.row += 1

    def exit(self):
        self.workbook.save(self.name)
        self.workbook.close()


def get_output_class(class_name):
    if class_name == "excel":
        return Excel()
    elif class_name == "htm":
        return Htm()
    return None


class Writer:
    def __init__(self, command: Command = None, argv=None):
        if not command:
            if not argv:
                argv = ["-h", "-i", "m", "l"]
            command = Command(argv)
        self.command = command

        self.file_in = {}
        for k in ("List", "Match"):
            if getattr(self.command, k):
                k = k.lower()
                file = f"{DATAFOLDER}/bid_day{k}_{self.command.day}.txt"  # bid_daylist_2023-07-06.txt
                self.file_in[k] = file

        self.file_out = {}
        for k in ("htm", "excel"):
            if getattr(self.command, k):
                self.file_out[k] = get_output_class(k)

    def output(self):
        for type, name in self.file_in.items():
            for out in self.file_out.values():
                out: Htm
                out.idx = 1
                out.init(name, type, self.command.match_no_keyword)
                out.head()
                out.body("top")

            with open(name, "r", encoding="utf-8") as f:
                idx = 0
                for line in f:
                    for out in self.file_out.values():
                        out: Htm
                        out.li(line)

            for out in self.file_out.values():
                out.body("bottom")
                out.exit()


def get_list(line: str) -> list:
    line_list = line.replace("\n", "").replace("\r", "").split("; ")
    return line_list


if __name__ == "__main__":
    command = Command(sys.argv)
    # argv = "-h -i mn -d 07-06".split(" ")
    # command = Command(argv)
    writer = Writer(command)
    writer.output()
