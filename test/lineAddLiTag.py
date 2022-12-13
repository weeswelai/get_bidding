import datetime as dt

def date_now_s(file_new=False):
    """ 返回当前日期
    Args:
        file_new (bool): 为True时返回小数点精确到
    """
    if file_new:
        return dt.datetime.now().strftime('_%Y_%m_%d-%H_%M_%S_%f')[:-3]
    else:
        return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

file = r"H:\Hasee_Desktop\vscode\python\get_zhaobiao\get_bidding_1\data\bid_list.txt"
match_file = r"data\match_list.txt"

list_html = f'{"".join(file.split(".")[: -1])}{date_now_s(True)}.html'
match_html = f'{"".join(match_file.split(".")[: -1])}{date_now_s(True)}.html'

if file:
    with open(file, "r", encoding="utf-8") as f, \
        open(list_html, "w", encoding="utf-8") as html:
        for idx ,line in enumerate(f):
            html.write(f"<li> {str(idx)}. {line.strip()} <li>\n")

if match_file:
    with open(match_file, "r", encoding="utf-8") as f, \
        open(match_html, "w", encoding="utf-8") as html:
        for idx ,line in enumerate(f):
            html.write(f"<li> {str(idx)}. {line.strip()} <li>\n")
