"""
用于测试网站的html使用什么样的形式解析
"""

import json
import sys
import re
import traceback
from sys import getsizeof

from module.log import logger
from module.web_brows import WebBrows, BidTag, Bid
from module.utils import *
# sys.stderr = logger.handlers[1].stream

# 正则测试网址: https://regex101.com/
"""
对于bid_settings.json中 task.rule 的解释
cut: 取出列表网页中列表所在的tag源码
    re_rule: 正则表达式
    rule_option: re.S的整型值,可使用 module.utils 中的print_re_options打印
                 对应大写字母的数字
next_pages: 下一页替换的正则表达式,和 re.sub直接替换页码,不使用额外参数

tag_list: 使用search_all方式得到的 包含所有项目的list

bid_tag: 获得list中各个项目的信息的规则
    命名方式为: [1]:[2]|[3]:[4]|[5]  , 具体使用时去掉[],仅修改 1~5的值
    共有5个部分, [1]和[2]组成 tag 的获取方式,[3]和[4]组成 属性的检索方式
    [5] 为使用find_all时需要返回的tag的下标.
    参数说明:
    [1]: 可选择: tagName_find_all, tagName_find, 为使用bs4的find_all方法
        或find方法得到tag
    [2]: tag所处结构,使用时可输入 列表或字符串,若输入字符串则为:
         "a.p.em",列表为 ["a","p","em"],具体实现为使用bs4的find方法并递归获得tag,
         该意思为返回第一个a标签中第一个p标签中的第一个em标签的tag
    [3]: tag中属性的名称, 如 "class" , "href" , 特别输入: "_Text", 
         "_Text" 用于直接获得tag的标签内容
    [4]: tag中属性的值,与 [3]一起使用,一般用于 当[3]名称为 class 时,
         取得class=[4]的tag的标签内容
    [5]: int类型,当[1] 为  tagName_find_all时返回的是搜索列表, 
         [5]作用为按选[5]的值对应下标的tag
    注意事项:
    1. 使用时必须含有一个 | , 即使 | 的左右为空,如 "|href:" , 
    2. 当 | 左右有值时必须用 ":" 隔开 [1]和[2], [3]和[4]
        错误示例:  "|href"  ,该示例没有使用 : 隔开 [3]和[4] ,
                   程序无法判断 href是[3]还是[4] 
    3. 使用 ""或None 时会返回None
    4. [5] 只有在 [1]为 tagName_find_all时使用,
    5. [2]只有在[1]为 tagName_find时使用
    6. 
bid: 正则解析得到的字符串
    date_cut: 正则表达式,对于 发布日期：2022-11-14 这样的字符串,
                需要提取出其中的日期部分


"""
rule= {
    "rule":{
        "cut": {
            "re_rule": "(<ul id=\"list1\">).*?(</ul>)",
            "rule_option": 16
        },
        "next_pages": "(?<=pageNo\=)\d{1,3}",
        "tag_list": "a",
        "bid_tag": {
            "name_r": "tagName_find:|title:",
            "date_r": "tagName_find:em|_Text:",
            "url_r": "tagName_find:|href:",
            "type_r": ""
        },
        "bid": {
            "date_cut": "\\d{4}([_\\-年])\\d{2}([_\\-月])\\d{2}(|日)"
        }
    }
}


web_page = "https://ebid.eavic.com/cms/channel/ywgg1/index.htm?pageNo=1"
page_html_f = r"./html_save/eavic.com cms channel ywgg1 index.htmpageNo=1_2022_12_20-16_58_28_081.html"
cut_html_f = r"./html_save/eavic.com cms channel ywgg1 index.htmpageNo=1_cut.html"
settings_json = "./bid_settings/bid_settings_t.json"
settings = read_json(settings_json)


openAndSaveUrl = 0
ruleTest = {
    "test": 1,
    "test_new_rule": 0,
    "get_bs_tag_list": {
        "cut_html": 0,
        "li_tag": 0,
        "bid_tag": 0,
        "bid": 0
    },
    "date": 0,
    "next_pages": 1
}

web_brows = WebBrows(rule)
if page_html_f:
    with open(page_html_f, "r", encoding="utf-8") as page_f:
            url_page = page_f.read()

if cut_html_f:
    with open(cut_html_f, "r", encoding="utf-8") as page_f:
        cut_page = page_f.read()

try:
    if openAndSaveUrl:  # 打开网址 保存url的response
        # 打开网址
        web_brows.open(url=web_page)
        # 保存decode后的源码
        web_brows.save_response(save_date=True)

    # 正则表达式测试
    if not ruleTest["test"]:
        print("ruleTest.test = 0, exit")
        sys.exit()

    if ruleTest["get_bs_tag_list"]["cut_html"]:
        # getsizeof page 最好不要小于51, ""的内存占用为51
        logger.info(f"test: page memory size: {getsizeof(url_page)}")
        
        web_brows.get_response_from_file(file=url_page)  # 将源码str输入web_brows对象
        if ruleTest["test_new_rule"]:  # 使用本文件中的测试rule
            web_brows.cut_html(rule["rule"]["cut"])  # 裁剪源码
        else:
            web_brows.cut_html()
        web_brows.save_response(url=web_page, 
                                rps=web_brows.html_list_match, extra="cut")
        logger.info(f"test: page memory size: {getsizeof(web_brows.html_list_match)}")

    if ruleTest["get_bs_tag_list"]["li_tag"]:
        # web_brows.get_response_from_file(file=url_page)
        # web_brows.cut_html(rule["cut"])
        tag_list = web_brows.get_bs_tag_list(page=cut_page, tag_rule=rule["rule"]["tag_list"])

    if ruleTest["get_bs_tag_list"]["bid_tag"]:
        bid_tag = BidTag(rule)

        for idx, tag in enumerate(tag_list):
            try:
                logger.debug(str(bid_tag.get(tag)))
            except:
                logger.error(f"idx: {idx} tag error: {tag},\n"
                            f"bid_tag rule: {bid_tag.get_now}\n"
                            f"{traceback.format_exc()}")
            # f"bid rule : {self.bid.get_now}\n"

    if ruleTest["date"]:  # 日期字符串的正则测试
        date_test = "发布日期：2022-11-14"  # 测试文本
        date_cut_rule = rule["rule"]["date_cut_rule"]  # 测试的正则表达式
        default = True  # 是否使用默认正则
        date_output = web_brows.re_get_time_str(  # 调用方法
            date_str=date_test,
            time_cut_rule=date_cut_rule,
            default=default )

        if default:
            date_cut_rule = r"\d{4}([_\-年])\d{2}([_\-月])\d{2}(|日)"
        logger.info(  # 打印结果
            f"ruleTest time: \"{date_test}\" becomes \"{date_output}\" " +
            f"through re: \"{date_cut_rule}\"")


    if ruleTest["next_pages"]:  # 下一页测试
        if rule["rule"]["next_pages"]:
            web_brows.get_next_pages(web_page, rule["rule"]["next_pages"])
        else:
            web_brows.get_next_pages(web_page)


except Exception:
    logger.error(f"test: {traceback.format_exc()}")



