import urllib


class RedirectorHandler(urllib.request.HTTPRedirectHandler):
    """Sets a new attribute to the request object when the request got a 301 redirect
    """
    def http_error_301(self, req, fp, code, msg, headers):
        if "location" in headers:
            redirect_url = headers["location"]
        elif "uri" in headers:
            redirect_url = headers["uri"]
        else:
            return
        req.redirect = redirect_url
        return super().http_error_301(req, fp, code, msg, headers)
