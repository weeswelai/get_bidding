from os.path import exists
from module.utils import date_now_s

DATAPATH = "./data"
MATCH = "bid_match"
LIST = "bid_list"
STBFUN = "scrollToBottom()"  # write_function 中的js函数名

TITLE = -4
DATE = -3
URL = -2
TYPE = -1

# "jdcg", "zzlh", "hkgy", "zhzb", "qjc", "cebpub"
WEB = ["jdcg", "zzlh", "hkgy", "zhzb", "qjc", "cebpub"]

# ["list", "match"]
TRANSFILE = ["list"]


def write_head(html, name: str, fileType):
    # html <head>标签, 显示标题
    html.write(f"""<head>
    <title>{name}_{fileType}</title>
</head>\n""")


def write_body(html, body):
    if body == "top":
        html.write(f"<body onload={STBFUN}>\n")
    elif body == "bottom":
        html.write("</body>")


def write_function(html):
    # 页面渲染完成后自动滚到底部
    html.write("""
    <script>
        // 页面渲染完成后自动滚到底部
        function scrollToBottom()
        {
            window.scrollTo(0, document.getElementsByTagName("body")[0].scrollHeight);
        }
    </script>
    """)


def labels_a(title, url):
    return f"<a href=\"{url}\">{title}</a>"


def wirte_li(html, line: str, idx, fileType):
    
    line_list = line.rstrip().split("; ")
    labelsA = labels_a(line_list[TITLE], line_list[URL])
    
    # TODO 有没有更好的写法
    if fileType == "match":  # match 一行会分为5个 [匹配关键词]; 标题; 日期; url; 类型
        html.write(f"<li>{str(idx)}. {line_list[0]}: {labelsA},"
                   f"{line_list[DATE]},{line_list[TYPE]}</li>\n")
    else:
        html.write(f"<li>{str(idx)}. {labelsA},"
                   f"{line_list[DATE]},{line_list[TYPE]}</li>\n")

def write_html(webName, fileType, txtFile):
    webFIle = get_file_name(fileType, webName, 'htm')
    with open(webFIle, "w", encoding="utf-8") as html:
        write_head(html, webName, fileType)
        write_body(html, "top")
        write_function(html)
        # TODO 有没有更好的写法
        idx = 1
        for line in txtFile:
            if not ";" in line:  # 忽略掉干扰信息
                html.write(f"<li> {line.strip()} <li>\n")
                continue
            wirte_li(html, line, idx, fileType)
            idx += 1
        write_body(html, "bottom")


def get_file_name(fileType, webName, Type):
    # 在 html 文件前缀前
    if Type == "txt":
        return f"{DATAPATH}/bid_{fileType}_{webName}.txt"
    elif Type in ["htm", "html"]:
        return f"{DATAPATH}/bid_{fileType}_{webName}{date_now_s(True)}.htm"


def main():
    # TODO 有没有更好的写法    
    for fileType in TRANSFILE:
        for webName in WEB:
            fileName = get_file_name(fileType, webName, "txt")
            if not exists(fileName):
                print(f"{fileName} is not exists")
                return

            with open(fileName, "r", encoding="utf-8") as file:
                write_html(webName, fileType, file)


if __name__ == "__main__":
    main()
