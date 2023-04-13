
class Proxy:

    def __init__(
            self,
            username: str,
            password: str,
            url: str,
            port: str,
    ):
        self.username = username
        self.password = password
        self.url = url
        self.port = port

    def format(self):
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.url}:{self.port}"
        else:
            return f"http://{self.url}:{self.port}"

    def as_dict(self):
        if self.username and self.password:
            return {
                'http': f"http://{self.username}:{self.password}@{self.url}:{self.port}",
                'https': f"http://{self.username}:{self.password}@{self.url}:{self.port}",
            }
        else:
            return {
                'http': f"http://{self.url}:{self.port}",
                'https': f"http://{self.url}:{self.port}",
            }

    @classmethod
    def from_string(cls, proxy_str):
        if not proxy_str:
            return None

        try:
            username, password, url, port = proxy_str.split(':')
        except (
                ValueError,
                TypeError,
        ):
            url, port = proxy_str.split(':')
            username, password = None, None

        return cls(
            username=username,
            password=password,
            url=url,
            port=port,
        )
