"""

"""
import sys
import traceback

from module.log import logger
from module.task_manager import TaskManager


def main(argv: list):
    restart = True if "-r" in argv else False
    bidTaskManager = TaskManager(restart=restart)
    try:
        bidTaskManager.loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        bidTaskManager.exit()


if __name__ == "__main__":
    main(sys.argv)
