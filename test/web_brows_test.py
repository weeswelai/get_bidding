"""
用于测试网站的html使用什么样的形式解析
"""

import json
import sys
import re
import traceback
from sys import getsizeof

from module.bid_log import logger
from module.bid_web_brows import web_brows, bid_web
from module.utils import *
from bid_start import bidTaskManager
# sys.stderr = logger.handlers[1].stream


bidTaskManager.build_new_task()

"""
对于bid_settings.json中的解释
cut_rule 取出列表网页中列表所在的tag源码
    cut_rule: 正则表达式
    rule_option: re.S的整型值,可使用 module.utils 中的print_re_options打印
                 对应大写字母的数字
    cut_idx: 由于使用的是re.search方法,需要group的值

date_cut_rule: 正则表达式,对于 发布日期：2022-11-14 这样的字符串,
               需要提取出其中的日期部分

list_rule: 获得list中各个项目的信息的规则
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
# """
rule= {
      "re": {
        "cut_rule": {
          "Enable": True,
          "re_rule": "(<ul class=\"searchList\">).*?(</ul>)",
          "rule_option": 16,
          "cut_idx": 0
        },
        "next_pages_rule": "(?<=_)\\d{1,3}(?<=\\d)",
        "date_cut_rule": "\\d{4}([_\\-年])\\d{2}([_\\-月])\\d{2}(|日)"
      },
      "list_rule": {
        "li_r": "tagName_all:li|",
        "name_r": "tagName_find:a.p.span|title:",
        "date_r": "tagName_find:i|class:fl dis_block release_date ",
        "url_r": "tagName_find:a|href:",
        "type_r": "tagName_find:a.p.em|_Text:"
      }
}


def open_save_html(url):
    """
    打开网址 保存url的response
    Args:
        url (str):  网址
    """
    # 保存请求头
    web_brows.init_req(url)
    # 打开网址
    web_brows.open_url_get_response()
    # 保存decode后的源码
    web_brows.save_response(save_date=True)


# web_page = r"http://www.365trade.com.cn/zbgg/index_1.jhtml"
web_page = "http://www.weain.mil.cn/cggg/jdgg/list.shtml"
page_html_f = r"./html_save/365trade.com.cn zbgg index_1.html"

if __name__ == "__main__":
    openAndSaveUrl = 1
    taskManagerFromFile = 0
    reTest = {
        "test": 0,
        "test_new_rule": 0,
        "cut_html": 0,
        "date": 0,
        "next_pages": 0
    }

    with open(page_html_f, "r", encoding="utf-8") as page_f:
            page = page_f.read()
    try:
        if openAndSaveUrl:
            open_save_html(web_page)  # 保存html

        # 正则表达式测试
        if reTest["test"]:
            if reTest["cut_html"]:
                # getsizeof page 最好不要小于51, ""的内存占用为51
                logger.info(f"test: page memory size: {getsizeof(page)}")
                # 将源码str输入web_brows对象
                web_brows.get_response_from_file(file=page)  
                if reTest["test_new_rule"]:  # 使用本文件中的测试rule
                    web_brows.cut_html(rule["re"]["cut_rule"])  # 裁剪源码
                    web_brows.get_list(list_rule=rule["list_rule"])
                else:
                    web_brows.cut_html()
                    web_brows.get_list()  # 得到list
                
            if reTest["date"]:  # 日期字符串的正则测试
                date_test = "发布日期：2022-11-14"  # 测试文本
                date_cut_rule = rule["date_cut_rule"]  # 测试的正则表达式
                default = True  # 是否使用默认正则
                date_output = web_brows.re_get_time_str(  # 调用方法
                    date_str=date_test,
                    time_cut_rule=date_cut_rule,
                    default=default )

                if default:
                    date_cut_rule = r"\d{4}([_\-年])\d{2}([_\-月])\d{2}(|日)"
                logger.info(  # 打印结果
                    f"reTest time: \"{date_test}\" becomes \"{date_output}\" " +
                    f"through re: \"{date_cut_rule}\"")

        if reTest["next_pages"]:  # 下一页测试
            if rule["re"]["test_new_rule"]:
                web_brows.get_next_pages(web_page, rule["re"]["next_pages_rule"])
            else:
                web_brows.get_next_pages(web_page)

        if taskManagerFromFile:  # 通过 bid_start 使用 bid_task对象
            newFlag = False
            # 创建项目列表页面,或进行翻页
            bidTaskManager.build_list_pages_brows()
            # 打开项目列表网址,保存html, 这里读取文件内容
            web_brows.url_response = page  # bidTaskManager.open_list_url()
            web_brows.url = page_html_f
            bidTaskManager.get_list_from_list_web_html()
            




    except Exception:
        logger.error(f"test: {traceback.format_exc()}")



