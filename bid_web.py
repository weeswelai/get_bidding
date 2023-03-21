"""
瞎写的,暂时不用考虑优化代码
"""

from logging import LogRecord
from os import _exit
from time import sleep

from pywebio import start_server
from pywebio.input import checkbox
from pywebio.output import *
from pywebio.session import eval_js, run_js

from module.log import logger, queue_handler
from module.task_manager import WebBreak
from module.utils import save_json
from bid_run import bidTaskManager

# BUTTON_TEST_SIZE = "40% 100px 60%"
LOG_TEST_SZIE = "70% 0px 70%"


class LogQueueNode:
    def __init__(self, text) -> None:
        self.text= text
        self.next: LogQueueNode = None

class LogQueue:
    tail: LogQueueNode = None  # 头指针
    head: LogQueueNode = None  # 尾指针
    node: LogQueueNode = None
    length = 0

    def add(self, text):
        node = LogQueueNode(text)
        if self.tail is None:
            self.head = node  # 头指针指向该节点
            self.tail = node  # 尾指针为该节点的指针
            self.length += 1

        elif self.length < 100:
            self.tail.next = node
            self.tail = node
            self.length += 1

        elif self.length >= 100:
            self.pop()
            self.add(text)
        

    def pop(self):
        if self.head is None:
            return None
        
        if self.head.next is None:
            text = self.head.text
            self.tail = None
            self.head = None
        else:
            text = self.head.text
            self.head = self.head.next
        self.length -= 1
        return text

    def __iter__(self):
        self.node = self.head
        return self
    
    def __next__(self):
        if self.node is None:
            raise StopIteration
        text = self.node.text
        self.node = self.node.next
        return text

class BidWeb:
    stroll = True

    def stroll_switch(self, btn_val):
        self.stroll = False if self.stroll else True

    def start_button(self, btn_val):
        # from bid_run import bidTaskManager
        try:
            logger.hr("START", 0)
            bidTaskManager.restart = True
            bidTaskManager.loop()
        except KeyboardInterrupt:
            bidTaskManager.exit()
            _exit(0)
        except WebBreak:
            save_json(bidTaskManager.settings, bidTaskManager.json_file)
        
    def stop_button(self, btn_val):
        # from bid_run import bidTaskManager
        bidTaskManager.break_ = True
        bidTaskManager.task.task_end = True
        self.stroll = False

    def exit(self, _):
        # save json
        # from bid_run import bidTaskManager
        bidTaskManager.exit()
        toast("结束程序")  # 弹窗
        _exit(0)  # 结束进程

    def main(self):
        from bid_run import bidTaskManager
        # root_scope = use_scope("ROOT")
        # root_scope = put_scope("ROOT").style('margin-top: 20px')
        put_row([
            put_scope(name="button"),
            put_buttons(["start"], onclick=self.start_button, scope="button"),
            put_buttons(["stop"], onclick=self.stop_button, scope="button"),
            put_buttons(["exit"], onclick=self.exit, scope="button"),
            put_buttons(["滚动日志"], onclick=self.stroll_switch, scope="button")]
            )

        put_row([
        put_scrollable([
            put_column([put_scope(name="log").style('margin-top: 0px; font-size: 10px')],size=LOG_TEST_SZIE)],
            height=600
            )
        ]).style("max-width: 7100px overflow-y:stroll")
        # with use_scope(name="log"):
        #     put_text("start", scope="log")

        print_log_queue()
        log_put = self.output_queue_log()

        try:
            while 1:
                next(log_put)
                sleep(0.5)
                if self.stroll and not bidTaskManager.sleep_now:
                    scroll_bottom()

        except KeyboardInterrupt:
            # from bid_run import bidTaskManager
            bidTaskManager.exit()
            _exit(0)

    def output_queue_log(self):
        while 1:
            while 1:
                if not queue_handler.queue.empty():
                    message = queue_handler.queue.get()
                    if isinstance(message, LogRecord):
                        message = message.message
                        log_queue.add(message)
                    put_text(message, scope="log")
                else:
                    break
            yield

    def run(self):
        try:
            start_server(self.main, port=40961, debug=False)
        except KeyboardInterrupt:
            
            bidTaskManager.exit()
            _exit(0)


def print_log_queue():
    try:
        log_print = iter(log_queue)
        while log_queue.length > 1:
            text = next(log_print)
            put_text(text, scope="log")
    except StopIteration:
        scroll_bottom()
        return None


def scroll_bottom():
    height = eval_js('document.getElementsByClassName("webio-scrollable scrollable-border")[0].scrollHeight')
    run_js('document.getElementsByClassName("webio-scrollable scrollable-border")[0].scroll(0,height)', height=height)


if __name__ == "__main__":
    log_queue = LogQueue()
    bid_web = BidWeb()
    bid_web.run()

