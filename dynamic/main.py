# coding: utf-8

import time
import threading
import atexit
import json
import logging
import logging.config
from datetime import datetime

import zhihu

from monitor import TopicMonitor
from utils import *
from utils import task_queue
from common import *
from config.dynamic_config import restart
from db import DB


class TaskLoop(threading.Thread):

    def __init__(self, routine=None, *args, **kwargs):
        self.routine = routine
        super().__init__(*args, **kwargs)

    def run(self):
        while True:
            if self.routine and callable(self.routine):
                self.routine()
            time.sleep(10)  # TODO: set to 60s
            count = len(task_queue)
            for _ in range(count):
                task = task_queue.popleft()
                task.execute()


def main(preroutine=None, postroutine=None):
    if os.path.isfile(logging_config_file):
        with open(logging_config_file, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)

    if restart:
        DB.drop_all_collections()

    validate_config(dynamic_config_file)
    if not validate_cookie(test_cookie):
        logger.error("invalid cookie")

    client = zhihu.ZhihuClient(test_cookie)
    TaskLoop(daemon=True).start()
    m = TopicMonitor(client)
    while True:
        # TODO: 考虑新问题页面采集消耗的时间，不能 sleep 60s
        if preroutine and callable(preroutine):
            preroutine()

        time.sleep(2)
        logger.debug(now_string())
        m.detect_new_question()

        try:
            if postroutine and callable(postroutine):
                postroutine()
        except EndProgramException:
            break


def cleaning():
    """
    Only for testing
    """
    from db import DB
    for collection in DB.db.collection_names():
        db[collection].drop()


if __name__ == '__main__':
    main()
    # atexit.register(cleaning)