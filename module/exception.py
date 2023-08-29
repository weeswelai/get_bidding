

class WebTooManyVisits(Exception):
    pass


class TooManyErrorOpen(Exception):
    pass


class CutError(Exception):
    pass


class ParseTagError(Exception):
    pass


# webio点击stop按钮时引发的异常
class WebBreak(Exception):
    pass
