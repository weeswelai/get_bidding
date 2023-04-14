import datetime as dt
import json
from module.utils import jsdump, date_now_s


def txt_to_html(file, html, match):
    with open(file, "r", encoding="utf-8") as f, \
            open(html, "w", encoding="utf-8") as html_f:
            idx = 1
            for line in f:
                if line[0] != "[":
                    html_f.write(f"<li> {line.strip()} <li>\n")
                    continue
                line_l = line.split("; ")
                html_t1 = line_l[0]
                html_a = f'<a href="{line_l[-2]}">{line_l[-4]}</a>'
                html_t2 = f"{line_l[-3]}, {line_l[-1]}"
                if match:
                    html_f.write(f"<li> {str(idx)}. {html_t1}: {html_a} ,{html_t2}<li>\n")
                else:
                    html_f.write(f"<li> {str(idx)}. {html_a} ,{html_t2}<li>\n")
                idx += 1

# def json_to_html(json_data=None, html=None, file=False):
#     if file:
#         with open (json_data, "r", encoding="utf-8") as f:
#             json_data = json.loads(f.read())
#     with open(html, "w", encoding="utf-8") as f:

# ["jdcg", "zzlh", "hkgy", "zhzb", "qjc"]
task_name = ["jdcg", "zzlh", "hkgy", "zhzb", "qjc"]
file = f"./data/bid_list_{task_name}.txt"  # ./data/bid_match_list_.txt
file = ""
match_file = f"./data/bid_match_list_{task_name}.txt"  # ./data/bid_match_list_.txt
json_read = "./data/api front list cggg list LMID=1149231276155707394&pageNo=1&purchaseType=公开招标&_t=1671776534822_2022_12_23-14_28_22_test.html"
json_file = f""
list_html = f'.{"".join(file.split(".")[: -1])}{date_now_s(True)}.htm'
match_html = f'.{"".join(match_file.split(".")[: -1])}{date_now_s(True)}.htm'

file_out = "match"  # list match

if file_out == "list":
    file_head = "list"
    match = False
elif file_out == "match":
    file_head = "match_list"
    match = True
else:
    exit()

if file:
    txt_to_html(file, list_html)

if isinstance(task_name, str) and match_file:
    txt_to_html(match_file, match_html)
elif isinstance(task_name, list):
    for name in task_name:
        match_file = f"./data/bid_{file_head}_{name}.txt"  # ./data/bid_match_list_{name}.txt  ./data/bid_list_{name}.txt
        match_html = f'.{"".join(match_file.split(".")[: -1])}{date_now_s(True)}.htm'
        txt_to_html(match_file, match_html, match)

if json_file:
    with open(json_read, "r", encoding="utf-8") as f:
        json_data = json.loads(f.read())
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(jsdump(json_data))
