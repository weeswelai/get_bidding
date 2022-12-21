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

def txt_to_html(file, html):
    with open(file, "r", encoding="utf-8") as f, \
            open(html, "w", encoding="utf-8") as html_f:
            idx = 1
            for line in f:
                if line[0] != "[":
                    html_f.write(f"<li> {line.strip()} <li>\n")
                    continue
                    
                html_f.write(f"<li> {str(idx)}. {line.strip()} <li>\n")
                idx += 1


file = r"./data/bid_list_hkgy.txt"
match_file = r"./data/bid_match_list_hkgy.txt"

list_html = f'.{"".join(file.split(".")[: -1])}{date_now_s(True)}.html'
match_html = f'.{"".join(match_file.split(".")[: -1])}{date_now_s(True)}.html'

if file:
    txt_to_html(file, list_html)

if match_file:
    txt_to_html(match_file, match_html)
