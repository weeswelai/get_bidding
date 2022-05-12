
import bid_task,get_url
import json
from threading import Timer
import datetime as dt

def class_creat(website,url="url"):
    return ("get_url.%s_get(\"%s\")"%(website,url))
#setting
json_file_name = r"H:\Hasee_Desktop\vscode\python\get_zhaobiao\get_bidding_1\json\module_1_run.json"
html_file = r"H:\Hasee_Desktop\vscode\python\get_zhaobiao\get_bidding_1\zzlh.txt"
run_flag = True
test_flag = True
if __name__ == "__main__":
    if(run_flag):
        #初始化任务列表
        task_mg = bid_task.task_manager(json_file_name,False)
        task_mg.build_task()
        if(task_mg.task_now_name == "zzlh"):
            # task_run = get_url.zzlh_get("file",html_file)
            task_run = get_url.zzlh_get()
            task_mg.upload_newest(data = task_run.get_search_list())
        # TODO 开始过滤每一页的招标信息

    if(test_flag):
        print(task_mg.data["zzlh"])
        pass

#判断任务状态
# if(task_prj.check_complete() == True):
#     #读取已保存的循环列表
#     pass
# elif(task_prj.check_complete() == False):
#     #继续上一次任务
#     pass
# elif(task_prj):
#     #以一周为界限开始爬取
#     pass



