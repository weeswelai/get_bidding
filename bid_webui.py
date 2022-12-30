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

# BUTTON_TEST_SIZE = "40% 100px 60%"
LOG_TEST_SZIE = "70% 0px 70%"

class BidWeb:
    stroll = False

    def stroll_switch(self, btn_val):
        self.stroll = False if self.stroll else True

    def start_button(self, btn_val):
        from bid_run import bidTaskManager
        try:
            logger.hr("START", 0)
            bidTaskManager.restart = True
            bidTaskManager.loop()
        except KeyboardInterrupt:
            bidTaskManager.exit()
            _exit(0)
        except WebBreak:
            save_json(bidTaskManager.settings, bidTaskManager.json_file)
        
    def exit_button(self, btn_val):
        from bid_run import bidTaskManager
        bidTaskManager.break_ = True
        bidTaskManager.task.task_end = True

    def exit(self, _):
        # save json
        from bid_run import bidTaskManager
        bidTaskManager.exit()
        toast("结束程序")  # 弹窗
        _exit(0)  # 结束进程

    def main(self):

        # root_scope = use_scope("ROOT")
        # root_scope = put_scope("ROOT").style('margin-top: 20px')
        put_row([
            put_scope(name="button"),
            put_buttons(["start"], onclick=self.start_button, scope="button"),
            put_buttons(["end"], onclick=self.exit_button, scope="button"),
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

        log_put = self.output_queue_log()

        try:
            while 1:
                next(log_put)
                sleep(1)
                if self.stroll:
                    height = eval_js('document.getElementsByClassName("webio-scrollable scrollable-border")[0].scrollHeight')
                    run_js('document.getElementsByClassName("webio-scrollable scrollable-border")[0].scroll(0,height)', height=height)

        except KeyboardInterrupt:
            from bid_run import bidTaskManager
            bidTaskManager.exit()
            _exit(0)

    def output_queue_log(self):
        while 1:
            while 1:
                if not queue_handler.queue.empty():
                    message = queue_handler.queue.get()
                    if isinstance(message, LogRecord):
                        message = message.message
                    put_text(message, scope="log")
                else:
                    break
            yield

    def run(self):
        try:
            start_server(self.main, port=40961, debug=True)
        except KeyboardInterrupt:
            from bid_run import bidTaskManager
            bidTaskManager.exit()
            _exit(0)

if __name__ == "__main__":
    bid_web = BidWeb()
    bid_web.run()