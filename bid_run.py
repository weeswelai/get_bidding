"""

"""
import sys
import traceback

from module.log import logger
from module.task_manager import TaskManager

bidTaskManager = TaskManager()


def main(argv: list):
    try:
        if "-r" in argv:
            logger.hr("task restart", 3)
            bidTaskManager.restart = True
        bidTaskManager.loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        bidTaskManager.exit()


if __name__ == "__main__":
    main(sys.argv)
