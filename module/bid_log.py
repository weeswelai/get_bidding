'''
本模块为日志模块
借鉴于 https://github.com/LmeSzinc/AzurLaneAutoScript/blob/master/module/logger.py
'''

import logging
import datetime 
import os

# 定义输出格式
file_formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d │ %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
web_formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d │ %(message)s', datefmt='%H:%M:%S')

# logger初始化
logger = logging.getLogger("bid_log")
logger.setLevel(level=logging.DEBUG)

# 设置 控制台handler
console_hdlr = logging.StreamHandler()
console_hdlr.setFormatter(console_formatter)
# console_hdlr.setFormatter(web_formatter)
logger.addHandler(console_hdlr) # 添加handler

# 自定义HR输出
logging.HR = 80
logging.addLevelName(logging.HR, "HR")

def rule(title="", characters="─"):
    '''自定义标题的输出规则,使用print对 handler的stream输出
    Args:
        title (str): 标题名,可谓
    '''
    space_text = 1
    length = len(title) + space_text * 2
    if length == 2:
        title = f"{characters * 119}"
    else:
        if length % 2 == 0:
            temp = 1 # 偶数
        else:
            temp = 0    # 奇数
        c_len1 = int((119 - length - temp) / 2)
        c_len2 = c_len1 + temp
        title = f"{characters * c_len1} {title} {characters * c_len2}"
    for hdlr in logger.handlers:
        # 只输出到 控制台流和文件流
        if isinstance(hdlr, logging.FileHandler) or \
           isinstance(hdlr, logging.StreamHandler):
            print(title, file=hdlr.stream) # 使用print 直接输出到file流

def hr(title, level=3):
    '''自定义hr输出函数，用于输出log标题
    Args:
        title (str): 大标题名称，可为""
        level (int): 大标题等级,范围 [0,3]
    '''
    title = str(title).upper()
    if level == 1:
        logger.rule(title, characters='═')
        logger.info(title)
    if level == 2:
        logger.rule(title, characters='─')
        logger.info(title)
    if level == 3:
        # logger.info(f"[bold]<<< {title} >>>[/bold]", extra={"markup": True})
        logger.info(f"<<< {title} >>>")
    if level == 0:
        logger.rule(characters='═')
        logger.rule(title, characters=' ')
        logger.rule(characters='═')

def set_file_logger(name="bid_log"):
    '''添加到logger对象中，用于 FileHandler初始化
    Args:
        name (str): FileHandler 输出的文件名
    '''
    # if '_' in name:
    #     name = name.split('_', 1)[0]
    log_file = f'./log/{datetime.date.today()}_{name}.txt'
    
    try:
        hdlr = logging.FileHandler(filename=log_file, mode="a", encoding="utf-8")
    except FileNotFoundError:
        os.mkdir('./log')
        hdlr = logging.FileHandler(filename=log_file, mode="a", encoding="utf-8")
    
    hdlr.setFormatter(file_formatter)
    logger.addHandler(hdlr)
    logger.log_file = log_file

def show():
    # logger输出示例,仅在 __name__ == "__main__" 时调用
    logger.info('INFO')
    logger.warning('WARNING')
    logger.debug('DEBUG')
    logger.error('ERROR')
    logger.critical('CRITICAL')
    logger.hr('hr0', 0)
    logger.hr('hr1', 1)
    logger.hr('hr2', 2)
    logger.hr('hr3', 3)
    # logger.info(r'Brace { [ ( ) ] }')
    # logger.info(r'True, False, None')

# 将输出到文件的handler添加进logger对象中
logger.set_file_logger = set_file_logger
logger.set_file_logger()

# 定义HR输出
logger.rule = rule
logger.hr = hr

# import bid_log 时启动
logger.hr('Start', level=0)

if __name__ == "__main__":
    show() # 输出示例