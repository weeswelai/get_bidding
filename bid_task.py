import json
import time

def date_now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class task_list:
    queue = ["zzlh","hkgy","jdcg"]
    #last_read_time = "2022-01-01 00:00::00"
    task_complete_time = "2022-01-01 00:00::00"
    run_time = "2022-01-01 00:00::00"
    #last_complete_time = "2022-01-01 00:00::00"
    #last_run_time = "2022-01-01 00:00::00"
    def __init__(self,last_queue="",task_complete_time="") -> None:
        if(last_queue != ""):
            self.queue = last_queue
        if(task_complete_time != ""):
            self.task_complete_time = task_complete_time
        self.run_time = time.strftime('%Y-%m-%d %H:%M:%S')
        #save run_time
        pass
    
    def complete_task(self):
        # Move the header element to the end of the queue
        task_name = self.queue.pop(0)
        self.queue.append(task_name)
        self.task_complete_time = time.strftime('%Y-%m-%d %H:%M:%S')
        #save task_complete_time
        pass
        return task_name

class bid_prj_state:
    web_sign = ""
    time_web_open = ""
    time_web_close = ""
    bid_prj_last_task_newest_time = ""
    bid_prj_last_task_newest_name = ""
    bid_prj_last_task_read_time = ""
    bid_prj_last_task_read_name = ""
    bid_prj_last_task_read_page = ""
    bid_prj_last_task_end_time = ""
    bid_prj_last_task_end_name = ""
    bid_prj_last_task_end_page = ""



    pass








if __name__ == "__main__":

    pass



