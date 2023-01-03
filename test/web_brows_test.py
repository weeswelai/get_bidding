# 测试网址的打开,规则解析
# 用于测试网址的html使用什么样的形式解析
# 使用 1 代替 True, 0 代替False

import traceback
from sys import getsizeof

from module.log import logger
from module.web_brows import ListWebBrows, BidTag, Bid
from module.utils import *
from module.judge_content import title_trie
# sys.stderr = logger.handlers[1].stream


"""
测试说明
1. 打开网页测试:
    将 openUrlAndSaveHtml 置为1 , 根据打开的网址修改 methond 的值
    method: 大部分网址使用 GET 方式, 目前只有 zhzb 使用 POST方式
    打开网址需要指定method: GET方式 或 POST方式, 通用测试网址 https://httpbin.org
    使用GET 方式则修改 get_url
    使用POST 方式则修改 post_url
"""
openUrlAndSaveHtml = 0  # 打开网址并保存response

# url 可直接复制 json 文件中的 url
# 如 json文件中 zzlh.货物.url = "http://www.365trade.com.cn/zbgg/index_1.jhtml?typeId=102" , 直接取双引号部分
# 且 json中 zzhl.urlConfig.method = "GET" 或  zzhl.urlConfig 没有 method属性时选用 GET方式
# url有两种形式, GET 为 str, POST为 dict, 若为POST则必须包含form信息

get_url = "http://www.365trade.com.cn/zbgg/index_2.jhtml?typeId=102"

# 一般情况下, post方式只需要修改 url 和 from的表单信息
post_url = {
    "url": "http://bid.aited.cn/front/ajax_getBidList.do",
    "form": {
        "classId": 151,
        "key": -1,
        "page": 1
    }
}

method = "get"  # post 或 get
method = method.upper()
url = get_url if method == "GET" else post_url
res_file = None

try:
    # 打开网址并保存response
    if openUrlAndSaveHtml:  # 打开网址 保存url的response
        from module.get_url import UrlOpen
        
        # 可在 UrlOpen中选择headers: url_open = UrlOpen(headers=test_headers, method=method)
        url_open = UrlOpen(method=method)
        response = url_open.open(url)  # 打开网址
        res_file = url_open.save_response(save_date=True,path="./html_test/")  # 保存decode后的源码
except Exception:
    logger.error(f"test: {traceback.format_exc()}")


_URL_TASK_NAME = {
    "search.ccgp.gov.cn": "zgzf",
    "www.plap.cn": "jdcg",
    "www.weain.mil.cn": "qjc",
    "www.365trade.com.cn": "zzlh",
    "ebid.eavic.com": "hkgy"
}

# TODO 测试说明可能写的非常啰嗦
# 该测试仅测试一页的功能, 若要测试一个任务, 请使用 task_test.py
"""
若注释或 test_settings变量过长, 请使用段落折叠功能
测试2. 规则测试
    以下内容为规则测试部分, 可从文件中测试具体的网页解析规则
    
测试步骤:
    0.  设置测试总开关 rule_test 为 1
    1.  选择 html 源码来源
        1.1 设置变量 get_html_from_open_url:
            为 1 衔接测试1, 直接使用测试1过程打开网址后的变量 response(网页decode后的html源码字符串) 作为 url_page的值
            为 0 不衔接测试1, 读取html文件.
        1.2 当 get_html_from_open_url 为0时html源码来源于html文件:
                设置 html_file 变量指向的html文件, url_page变量的值为 open(html_file).read()
    2.  设置 settings_from_json 的值: 选择任务 settings的来源
        2.1 为 1 读取本地json文件,默认 ./bid_settings/bid_settings.json
            2.1.1 当 get_html_from_open_url 为 0, 即不衔接测试1时:
                同时设置变量 task_name 的值, 要和测试的html有相同的任务名, 如 zzlh, qjc, hkgy等
        2.2 为 0 使用 变量 test_settings
    3.  打开要测试的功能的开关变量,将开关变量设为1, 参考下面的开关变量,测试说明
        从开关变量 _cut_html 到 _title_trie 为止, 开启后一个开关必须保证前一个开关也是打开的
            如 _li_tag = 1 时, cut_html也必须为1
    4.  对于一个网址的爬取和解析,如: http://www.365trade.com.cn/zbgg/index_1.jhtml?typeId=102
        将从 获得 html源码开始, 按 裁剪源码-提取tag_list-获得tag基本信息-获得项目基本信息-获得项目信息

开关变量,测试说明:
    以下说明将使用 "rule" 代替 "settings中的rule属性的值"
    1. _cut_html:
        裁剪源码: 使用rule 中的cut 属性的值进行源码的裁剪, 过程为使用 cut属性的正则提取符合要求的html源代码字符串
        使用 web_brows.cut_html() 方法
        该过程结束后得到变量 html_cut(str)
    2. _li_tag:
        获取 tag_list, 先使用bs 使用 bs4模块的 find_all 检索tag, 返回一个 list
        如 "tag_list": "li" , 则 返回包含所有 <li> 标签的list
        使用 web_brows.get_tag_list() 方法, 先对输入的 html_cut 变量(str)用BeautifulSoup解析
        解析后 使用 find_all 检索, 得到变量 tag_list(list)
    3. _bid_tag:
        先初始化对象 bid_tag(web_brows.BidTag) 和对象 bid(web_brows.Bid)
        用 bid_tag.get() 方法解析 tag_list中每个 tag, 得到的信息存在 message属性中
        该过程使用到 rule 的 "bid_tag" 规则
    4.  _bid:
        用 bid.receive() 方法对 bid_tag 对象中的 message进一步提取
        结果存在bid 的message属性中
        该过程使用了 rule 的 "bid" 规则
    5. _title_trie:
        使用 title trie 对 bid.message 中第一个元素,也就是对项目标题进行关键词检索
        打印检索到的关键词
        该过程需要参考 module.title_trie.py 和 ./test/前缀树.txt
    6. _next_pages:
        根据 rule 中 "next_pages" , 先用 re.search 得到页码, 再使用 re.sub 对 页码进行替换
        使用 web_brows.get_next_pages() 方法, 对于method为 POST 的url则修改form的值
    
变量说明:
    以下为需要手动修改的变量:
    test_settings: 测试用settings, 保存了任务的规则,也可以使用 json文件中的 settings
                    若要使用文件中的settings , 须将 settings_from_json 设为1
    html_file: 要读取的 html文件
    JSON_FILE: 默认的json配置文件路径
    task_name: 要测试的任务名, 如 zzlh, qjc, hkgy等
"""

# TODO 需进一步修改
# 正则测试网址: https://regex101.com/
"""
以下注释为对于bid_settings.json中 task.rule 的解释, 也是对下面 test_settings变量中 rule部分的解释

cut: 取出列表网页中列表所在的tag源码, 由于 cut_html 默认使用 re.search().group(), 所以必须一次性得到符合要求的部分
    re_rule: 正则表达式
    rule_option: re.S的整型值,可使用 module.utils 中的print_re_options打印
                 对应大写字母的数字

next_pages: 下一页替换的正则表达式,使用 re.sub直接替换页码,不使用额外参数

tag_list: 使用search_all方式得到的 包含所有项目的list

bid_tag: 获得list中各个项目的信息的规则
    命名方式为: [1]:[2]|[3]:[4]|[5]  , 具体使用时去掉[],仅修改 1~5的值
    共有5个部分, [1]和[2]组成 tag 的获取方式,[3]和[4]组成 属性的检索方式
    [5] 为使用find_all时需要返回的tag的下标.
    参数说明:
    [1]: 可选择: tagName_all, tagName_find, 为使用bs4的find_all方法
        或find方法得到tag
    [2]: tag所处结构,使用时可输入 列表或字符串,若输入字符串则为:
         "a.p.em",列表为 ["a","p","em"],具体实现为使用bs4的find方法并递归获得tag,
         该意思为返回第一个a标签中第一个p标签中的第一个em标签的tag
    [3]: tag中属性的名称, 如 "class" , "href" , 特别输入: "_Text", 
         "_Text" 用于直接获得tag的标签内容
    [4]: tag中属性的值,与 [3]一起使用,一般用于 当[3]名称为 class 时,
         取得class=[4]的tag的标签内容
    [5]: int类型,当[1] 为  tagName_all时返回的是搜索列表, 
         [5]作用为按选[5]的值对应下标的tag
    注意事项:
    1. 使用时必须含有一个 | , 即使 | 的左右为空,如 "|href:" , 
    2. 当 | 左右有值时必须用 ":" 隔开 [1]和[2], [3]和[4]
        错误示例:  "|href"  ,该示例没有使用 : 隔开 [3]和[4] ,
                   程序无法判断 href是[3]还是[4] 
    3. 使用 ""或None 时会返回None
    4. [5] 只有在 [1]为 tagName_all时使用,
    5. [2]只有在[1]为 tagName_find时使用
    6. tagName_all 与 [4]和[5]同时使用的情况下, 只会搜到一个值,此时 [5]为0
bid: 正则解析得到的字符串
    date_cut: 正则表达式,对于 "发布日期：2022-11-14" 这样的字符串,
                需要提取出其中的日期部分, 舍弃掉 "发布日期："等多余字符
"""

test_settings = {
"headers": {
      "User-Agent": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
      ],
      "Cookie": []
    },
    "urlConfig": {
      "root": {
        "default": "http://bid.aited.cn"
      },
      "method": "POST"
    },
    "rule": {
      "cut": {
        "re_rule": "<li>.*?(?=,)",
        "rule_option": 16
      },
      "next_pages": "",
      "tag_list": "li",
      "bid_tag": {
        "name_r": "tagName_find:a|title:",
        "date_r": "tagName_find:div.span|_Text:",
        "url_r": "tagName_find:a|href:",
        "type_r": ""
      },
      "bid": {
        "name_cut": "(?<=\").*?(?=\\\)",
        "date_cut": "\\d{4}([_|\\-|年])\\d{1,2}([_|\\-|月])\\d{1,2}(日|)",
        "url_cut": "(?<=\.\.).*?(?=\\\)"
      }
    }
}

rule_test = 0  # 规则测试总开关
get_html_from_open_url = 0  # 衔接测试1打开网址和测试2网页解析

settings_from_json = 0  # 0: 使用本文件中test_settings, 1: 使用json file的setting,需要指定任务名
_cut_html = 0  # 裁剪html源码并保存
_li_tag = 0    # 从源码中获得项目列表, 这里使用的是 cut_html_f
_bid_tag = 0   # 测试项目列表中项目基本信息提取
_bid = 0      # 测试项目信息获取
_title_trie = 0  # 前缀树搜索测试
_next_pages = 0  # 测试获得下一页网址,需要 全局 url变量

html_file = r""
JSON_FILE = "./bid_settings/bid_settings.json"
json_settings = read_json(JSON_FILE)  # 读取json文件为dict对象

task_name = "test"
if get_html_from_open_url:
    if isinstance(url, dict):
        task_name = "zhzb"
    else:
        for u, name in _URL_TASK_NAME.items():
            if u in url:
                task_name = name
                break

settings = json_settings[task_name] if settings_from_json else test_settings
web_brows: ListWebBrows.Html = ListWebBrows.init(settings, task_name)

try:
    # 使用本地文件或使用测试1得到的html源码
    if get_html_from_open_url:
        url_page = response
    elif html_file and html_file[-1] != "/":
        with open(html_file, "r", encoding="utf-8") as page_f:
            url_page = page_f.read()
    else:
        print("no url response read")
        exit(1)

    if rule_test:
        # 测试裁剪源码, 得到 html_cut 变量
        if _cut_html:
            # getsizeof page 最好不要小于51, ""的内存占用为51
            logger.info(f"test: page memory size: {getsizeof(url_page)}")
            
            web_brows.get_response_from_file(file=url_page)  # 将源码str输入web_brows对象
            web_brows.decode_response()
            try:
                html_cut = web_brows.cut_html()
            except AttributeError as error:
                logger.error(f"{error}\n{traceback.format_exc()}")
                exit(1)
            logger.info(f"test: page memory size: {getsizeof(web_brows.html_cut)}")

            # 保存裁剪后的html源码, 若不想保存请将下面语句注释掉
            # web_brows.save_response(rps=web_brows.html_cut, url="cut_test_html",
            #                         path="./html_test/", extra="cut")
        else:
            html_cut = url_page

        # 测试获得项目列表
        if _li_tag:
            # web_brows.get_response_from_file(file=url_page, save="html_cut")
            # web_brows.cut_html(settings["rule"]["cut"])

            tag_list = web_brows.get_tag_list(
                page=html_cut, tag_rule=settings["rule"]["tag_list"])
            logger.info(f"tag_list len: {len(tag_list)}")

        # 测试项目列表中项目基本信息提取
        if _bid_tag:
            bid_tag = BidTag(settings)
            bid = Bid(settings)
            for idx, tag in enumerate(tag_list):
                try:
                    bid_tag.get(tag)
                    # logger.debug(str(bid_tag.message))
                except:
                    logger.debug(f"bid_tag: {bid_tag.message}")
                    logger.error(f"idx: {idx} tag error: {tag},\n"
                                f"bid_tag rule: {bid_tag.get_now}\n"
                                f"{traceback.format_exc()}")

                # 测试项目信息获取
                if _bid:
                    bid.receive(*bid_tag.message)
                    logger.debug(bid.message)

                # 前缀树搜索
                if _title_trie:
                    logger.info("title_trie.search_all: "
                                f"{title_trie.search_all(bid.message[0])}")

    # 下一页测试
    if _next_pages:
        web_brows.get_next_pages(url, settings["rule"]["next_pages"])

except Exception:
    logger.error(f"test: {traceback.format_exc()}")



