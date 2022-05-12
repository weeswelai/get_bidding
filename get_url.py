

import urllib.request as urlreq
import re
import xml.dom.minidom




class message_html:
    #信息保存在html源码中
    def __init__(self) -> None:
        self.page = 1
        self.source_reponse = urlreq.urlopen(self.url)
        self.source_reponse_read = self.source_reponse.read().decode('utf-8')
    
    def get_reponse(self):
        self.source_reponse = urlreq.urlopen(self.url)
        self.source_reponse_read = self.source_reponse.read().decode('utf-8')

class message_js:
    #信息保存在java script 的动态内容中
    pass


class get_html(message_html):

    def __init__(self,url) -> None:
        self.url = url
        super().__init__()
        


class zzlh_get():
    data_list = [{
        "url": "",
        "name": "",
        "date": "",
        "type": ""
    }]
    def __init__(self,file="url",url="") -> None:
        '''
        file: "url" or "file"
        url: zzlh url or html file path ,
        if url = "" -> url = "http://www.365trade.com.cn/zbgg/index_1.jhtml"
        '''
        self.page = 1
        self.root_url = "www.365trade.com.cn"
        self.data_list = []
        if(file == "url"):  #url不为空为本地文件测试用
            if(url == ""):
                self.url = r"http://www.365trade.com.cn/zbgg/index_1.jhtml"
            else:
                self.url = url
            self.source_reponse = urlreq.urlopen(self.url).read().decode('utf-8')
        elif(file == "file"):
            self.url = "html_file"
            self.source_reponse = open(url,"r",encoding="utf-8").read()

    #TODO 


    def get_search_list(self):

        def get_content(node,tag_name): #xml中tag的内容
            data = node.getElementsByTagName(tag_name)[0].childNodes[0].data
            return data
        def get_class(node,tag_name,class_name): #xml中tag中属性的值 
            data = node.getElementsByTagName(tag_name)[0].getAttribute(class_name)
            return data
        html_data = re.findall('<ul class="searchList">(.*?)</ul>',self.source_reponse,flags = re.S)[0]
        self.source_reponse = r'<note name="zzlh">' + html_data + r'</note>'    #加根节点，转为xml文档
        dom_tree = xml.dom.minidom.parseString(self.source_reponse)
        li_tag = dom_tree.getElementsByTagName("li")
        for node in li_tag:
            dict_data = {
                "url": self.root_url + get_class(node,"a","href"),
                "name": get_class(node,"span","title"),
                "date": get_content(node,"i").replace("发布日期：",""),
                "type": get_content(node,"em")
            }
            self.data_list.append(dict_data)
        return self.data_list[0]

        #去除多余标签
    def upload(self):
        # self.url = 
        pass

    def next_page():
        # TODO 实现翻页
        pass


    pass


if __name__ == "__main__":
    json_file_name = r"H:\Hasee_Desktop\vscode\python\get_zhaobiao\get_bidding_1\json\module_1_2022-05-10_17-57-30-559346.json"
    html_file = r"H:\Hasee_Desktop\vscode\python\get_zhaobiao\get_bidding_1\zzlh.txt"
    task_run = zzlh_get("file",html_file)
    task_run.get_search_list()
    print(task_run.data_list[0])


