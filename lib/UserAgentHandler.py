import urllib


class UserAgentHandler(urllib.request.HTTPHandler):
    def __init__(self, user_agent):
        super().__init__()
        self._user_agent = user_agent

    def http_request(self, request):
        request.headers["User-Agent"] = self._user_agent
        return super().http_request(request)

    def https_request(self, request):
        request.headers["User-Agent"] = self._user_agent
        return super().http_request(request)
