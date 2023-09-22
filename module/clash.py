from get_url import HEADERS, TIMEOUT
from module.get_url import RequestBase


class Clash(RequestBase):

    def __init__(self, config):
        self.controller = config["controller"]
        self.headers = {"Authorization": f"Bearer {config['secret']}"}
        self.proxies_key = ""

    def get_proxies_dict(self, key=""):
        key
        url = f"http://{self.controller}/proxies"
        self._get(url, headers=self.headers)
        return self._response

