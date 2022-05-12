import json
import datetime as dt
import get_url

class test:
    def __init__(self) -> None:
        self.data = ""
        pass

def save_json(data="",json_file="",indent=4,creat_new=False,class_prj=""):
    if(json_file == ""):
        json_file = class_prj.json_file
        data = class_prj.data
    if(creat_new):  #是否覆盖原文件
        json_file = json_file.split(".json")[0] + date_now(True) + ".json"
    with open(json_file,"w",encoding="utf-8") as json_file_w:
        if(indent == 0):
            json.dump(data,json_file_w,ensure_ascii=False)
        elif(indent > 0):   
            json.dump(data,json_file_w,indent=indent,ensure_ascii=False)

def date_now(name_flag=False):
    if(name_flag):
        return dt.datetime.now().strftime('_%Y-%m-%d_%H-%M-%S-%f')
    else:
        return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
class task_manager:
    def __init__(self,json_file,creat_new=True,save=True):
            #初始化 
        with open(json_file,"r",encoding="utf-8") as file_o:
            self.data = json.load(file_o)
        if(self.data["task"]["queue"] in [[],[""],""]):
            self.data["task"]["queue"] = ["zzlh","hkgy","jdcg"]  #默认

        self.data["task"]["run_time"] = date_now()
        if(save):   #保存当前文件，可选是否保存新副本，由于此处只修改run_time,所以可以修改源json
            #是否覆盖源文件
            save_json(self.data,json_file,4,creat_new)
        
        self.json_file = json_file
        self.queue = self.data["task"]["queue"]
        self.task_now_name = self.queue[0]
        self.task_now_flag = self.data[self.task_now_name]["newest_task"]["flag"]

    def complete_task(self,creat_new=False):
        # Move the header element to the end of the queue
        task_name = self.queue.pop(0)
        self.queue.append(task_name)
        self.task_complete_time = dt.datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        #save queue and task_complete_time
        self.data["task"]["queue"] = self.queue
        self.data["task"]["complete_time"] = self.task_complete_time 
        self[task_name]["complete_flag"]
        save_json(self.data,self.json_file,4,True)
        return task_name

    

    def build_task(self,creat_new=False):
        '''
        if creat_new = True ,creat a new json file.
        '''
        def build_new_task(self):
            self.data["task"]["task_now_name"] = self.task_now_name
            self.data[self.task_now_name]["task_end"]["date"] = str(dt.date.today() - dt.timedelta(days=8))
            self.data[self.task_now_name]["newest_task"]["flag"] = self.data[self.task_now_name]["recent_task"]["flag"] = False
            self.data[self.task_now_name]["task_end"]["flag"] = "no record"
            save_json(self.data,self.json_file,4)

        if(self.task_now_flag in ["none","",None," "]):
            build_new_task(self)
            print("json file has no record of last task : %s"%self.json_file)

        elif(self.task_now_flag):
            pass
        elif(not self.task_now_flag):
            pass

    def upload_newest(self,task_run="",data:dict=""):
        '''
        task_run : 关于get_bid 的对象实例
        '''
        if(task_run != ""):
            self.data["zzlh"]["newest_task"]["name"] = task_run.data_list[0]["name"]
            self.data["zzlh"]["newest_task"]["date"] = task_run.data_list[0]["date"]
            self.data["zzlh"]["newest_task"]["url"] = task_run.data_list[0]["url"]
        elif(data != ""):
            self.data["zzlh"]["newest_task"]["name"] = data["name"]
            self.data["zzlh"]["newest_task"]["date"] = data["date"]
            self.data["zzlh"]["newest_task"]["url"] = data["url"]
        save_json(class_prj=self)

    def start_task(self):
        command_txt = "" + ""
        task_run = eval() 
        pass

    #TODO 翻页更新        




class bid_state:
    def __init__(self,data,web_sign) -> None:
        self.web_sign = data[web_sign]["web_sign"]
        self.last_task_complete = data[web_sign]["last_task_complete"]
        self.time_web_open = data[web_sign]["time_web_open"]
        self.time_web_close = data[web_sign]["time_web_close"]  #已完成，未完成，无记录
        self.last_task_newest_time = data[web_sign]["last_task_newest_time"]
        self.last_task_newest_name = data[web_sign]["last_task_newest_name"]
        self.last_task_read_time = data[web_sign]["last_task_read_time"]
        self.last_task_read_name = data[web_sign]["last_task_read_name"]
        self.last_task_read_page = data[web_sign]["last_task_read_page"]
        self.last_task_end_time = data[web_sign]["last_task_end_time"]
        self.last_task_end_name = data[web_sign]["last_task_end_name"]
        self.last_task_end_page = data[web_sign]["last_task_end_page"]


    pass



class zzlh_state(bid_state):
    
    pass







if __name__ == "__main__":
    json_file_name = r"json\module_1_2022-05-10_17-57-30-559346.json"

    pass



