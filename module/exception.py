

class WebTooManyVisits(Exception):
    def __init__(self, delay=None, *args: object) -> None:
        self.delay = delay
        super().__init__(*args)


class TooManyErrorOpen(WebTooManyVisits):
    pass


class CutError(Exception):
    delay = None


class TaskError(WebTooManyVisits):
    pass


class ParseTagError(Exception):
    pass


# webio点击stop按钮时引发的异常
class WebBreak(Exception):
    pass
