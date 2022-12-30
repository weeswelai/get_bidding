from logging import LogRecord
from os import _exit
from time import sleep

from pywebio import start_server
from pywebio.output import *

from module.log import logger, queue_handler
from module.task_manager import WebBreak
from module.utils import save_json


def start_button(btn_val):
    from bid_run import bidTaskManager
    try:
        logger.hr("START", 0)
        bidTaskManager.restart = True
        bidTaskManager.loop()
    except KeyboardInterrupt:
        bidTaskManager.exit()
    except WebBreak:
        save_json(bidTaskManager.settings, bidTaskManager.json_file)
        

def exit_button(btn_val):
    from bid_run import bidTaskManager
    bidTaskManager.break_ = True


def exit(_):
    # save json
    from bid_run import bidTaskManager
    bidTaskManager.exit()
    toast("结束程序")  # 弹窗
    _exit(0)  # 结束进程

# BUTTON_TEST_SIZE = "40% 100px 60%"
LOG_TEST_SZIE = "70% 0px 70%"

def main():
    put_row([
        put_scope(name="button"),
        put_buttons(["start"], onclick=start_button, scope="button"),
        put_buttons(["end"], onclick=exit_button, scope="button"),
        put_buttons(["exit"], onclick=exit, scope="button")]
        ),
    put_row([
    put_scrollable([
        put_column([put_scope(name="log").style('margin-top: 0px')],size=LOG_TEST_SZIE)],
        height=500
        )
    ])
    # with use_scope(name="log"):
    #     put_text("start", scope="log")

    log_put = output_queue_log()
    try:
        while 1:
            next(log_put)
            sleep(0.1)
    except KeyboardInterrupt:
        from bid_run import bidTaskManager
        bidTaskManager.exit()
        _exit(0)

def output_queue_log():
    while 1:
        if not queue_handler.queue.empty():
            message = queue_handler.queue.get()
            if isinstance(message, LogRecord):
                message = message.message
            put_text(message, scope="log")
        yield

try:
    start_server(main, port=40961, debug=True)
except KeyboardInterrupt:
    from bid_run import bidTaskManager
    bidTaskManager.exit()
    _exit(0)

