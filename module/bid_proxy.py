import json
from logging import Logger
from urllib.parse import quote

from requests import Session, Response

from module.utils import deep_get

config_example = {
    "clash": {
        "proxy_list": [
            "p1",
            "p2",
            "p3"
        ],
        "group": "",
        "controller": "127.0.0.1:9090"
    }
}

TIMEOUT_MAX = 1000  # 1000ms
TIMEOUT_TEST_URL = "http://www.gstatic.com/generate_204"


class Clash:
    _proxy = None
    proxy_next = None
    proxy_timeout: dict = None
    logger: Logger = None

    # config
    proxy_list: list = None
    group: str = None
    controller: str = "127.0.0.1:9090"

    # request
    secret = None
    headers: dict  # must have "Content-Type": "application/json" and "Authorization": f"Bearer {secret}"
    url_head: str  # f"http://{self.controller}"
    response: Response
    session = Session()

    def __init__(self, config=None, secret=None, headers=None, logger: Logger = None):
        self.init(config, secret, headers, logger)

    def init(self, config=None, secret=None, headers=None, logger: Logger = None):
        self._log("Init clash")
        if config:
            config = deep_get(config, "Clash")
            for name, value in config.items():
                setattr(self, name, value)
        secret = secret or self.secret
        self.headers = headers or {"Authorization": f"Bearer {secret}"}
        self.headers["Content-Type"] = "application/json"  # Change the proxy must be "application/json"
        self.url_head = f"http://{self.controller}"
        if logger:
            self.logger = logger
        if not self.group:
            self.set_group()

    def open(self, method:str, url, data=None, headers=None, **kwargs):
        headers = headers or self.headers
        method = method.lower()
        if isinstance(data, dict):
            data = json.dumps(data)
        self.response = self.session.request(method, url, 
                                data=data, headers=headers, **kwargs)
        return self.response

    def set_group(self):
        url = f"{self.url_head}/providers/proxies"
        response = self.open("GET", url)
        assert response.status_code == 200, f"clash config group is \"{self.group}\", and can't open {url}"
        groups = json.loads(response.text)["providers"]
        for group in groups:
            if group == "default":
                continue
            else:
                self.group = group
                self._log(f"Set group: {group}")
                return group

    @property
    def proxies(self):
        """
        获得代理列表
        """
        proxies = []
        if not self.group:
            self.set_group()
        url = f"{self.url_head}/proxies/{self.group}"
        text = self.open("GET", url=url).text
        proxies = json.loads(text)
        return proxies

    @property
    def proxy(self):
        if self._proxy is None:
            self.get_current_proxy()
        return self._proxy

    @proxy.setter
    def proxy(self, proxy:str):
        """
        Change current proxy,
        you are advised to use close_current_connections before closing
        """
        if not proxy or not self.group:
            return
        group = quote(self.group)
        url = f"{self.url_head}/proxies/{group}"
        data = {"name": proxy}
        code = self.open("PUT", url, data=data).status_code
        if code != 204:
            self._log(f"Clash change proxy Error, {code} {self.response.text}"
                      f"url: {url}\nproxy: \"{proxy}\"", level="error")
        else:
            self._proxy = proxy
            self._log(f"Clash proxy change to \"{proxy}\"")

    def find_proxy(self):
        """
        Find next proxy whose timeout < 1000ms
        """
        current_proxy = self.get_current_proxy()
        proxy_list = self.proxy_list or self.proxies
        if current_proxy in proxy_list:
            idx = proxy_list.index(current_proxy)
            proxy_list = proxy_list[idx:] + proxy_list[: idx]
        for proxy in proxy_list:
            if proxy == current_proxy:
                continue
            if self.get_proxy_timeout(proxy) < 1000:
                self._log(f"Find an available proxy: \"{proxy}\"")
                break
            else:
                proxy = None
        if not proxy:
            self._log("Not available proxy")
            return current_proxy
        return proxy

    def close_all_connections(self):
        """
        Close connection for previous proxy,
        used before switch to new proxy
        """
        url = f"{self.url_head}/connections"
        code = self.open("DELETE", url).status_code
        if code != 204:
            self._log("Clash close all connections error, "
                     f"{code} {self.response.text}", "error")
        else:
            self._log("Clash closed all connections Successfully")

    def close_connections(self, host):
        self._log(f"Close connect: {host}")
        url = f"{self.url_head}/connections"
        response = self.open("GET", url)
        if response.status_code != 200:
            return
        connections = json.loads(response.text)
        for connect in connections["connections"]:
            if host == connect["metadata"]["host"]:
                connect_id = connect["id"]
                url = f"{self.url_head}/connections/{connect_id}"
                self.open("DELETE", url)

    def switch_proxy(self):
        self._log(f"Proxy is \"{self.proxy}\" now")
        proxy = self.find_proxy()
        self.close_all_connections()
        self.proxy = proxy

    def get_proxy_timeout(self, proxy=None) -> int:
        if proxy is None:
            proxy = self.proxy or self.get_current_proxy()
        url = f"{self.url_head}/proxies/{proxy}/delay"
        params = {
            "timeout": "5000",
            "url": TIMEOUT_TEST_URL
        }
        code = self.open("GET", url=url, params=params).status_code
        delay = None
        if code == 200:
            response = json.loads(self.response.text)
            delay = int(response["delay"])
        self._log(f"Test: {code}, \"{proxy}\" delay: {delay}")
        return delay

    def get_current_proxy(self):
        if self.group is None:
            self._log("Group is None, please set group")
            return None
        proxies = self.proxies
        proxy = deep_get(proxies, f"now")  # f"proxies.{self.group}.now"
        self._log(f"Current proxy is {self.group}/{proxy}")
        self._proxy = proxy
        return proxy

    def _log(self, log:str, level="info"):
        if self.logger:
            fun = getattr(self.logger, level)
            fun(log)
        else:
            print(log) 

    # def check_rules(self):
    #     """
    #     寻找并添加对应网址的规则
    #     """
    #     pass

    # def switch_profiles(self):
    #     """
    #     """
    #     pass

if __name__ == "__main__":
    from module.config import CONFIG
    self = Clash(CONFIG.config)