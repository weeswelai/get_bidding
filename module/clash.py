from get_url import HEADERS, TIMEOUT

from module.get_url import RequestBase


"""
伪代码
"""



class Clash(RequestBase):

    def __init__(self, config):
        self.controller = config["controller"]
        self.headers = {"Authorization": f"Bearer {config['secret']}"}
        self.proxies_key = ""

    @property
    def proxies(self):
        """
        获得代理列表
        """
        url = f"http://{self.controller}/proxies"
        self._get(url, headers=self.headers)
        return self._response

    @property.setter
    def proxies(self, proxies):
        pass

    def switch_next_proxies(self):
        """
        切换到下一个可用代理
        """
        pass

    def close_current_connections(self):
        """
        close connection for previous proxies,
        used before switch to new proxies
        
        """
        pass

    def check_rules(self):
        """
        寻找并添加对应网址的规则
        """
        pass

    def switch_profiles(self):
        """
        切换节点
        """
        pass