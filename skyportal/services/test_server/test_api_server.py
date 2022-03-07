import glob
import json
import datetime
import re
import os

import vcr
import tornado.ioloop
import tornado.httpserver
import tornado.web
from suds import Client
import requests

from baselayer.app.env import load_env
from baselayer.log import make_log


def get_cache_file_static():
    """
    Helper function to get the path to the VCR cache file for requests
    that must be updated by hand in cases where regular refreshing is
    infeasible, i.e. limited access to the real server.

    To update this server recording:
    1) delete the existing recording
    2) re-run all tests (with API keys for telescopes in place)
    3) replace any secret information (such as API keys) with dummy values
    4) commit recording

    """
    return "data/tests/test_server_recordings_static.yaml"


def get_cache_file():
    """
    Helper function to get the path to the VCR cache file.
    The function will also delete the existing cache if it is too old.
    """
    files = glob.glob("cache/test_server_recordings_*.yaml")
    today = datetime.date.today()

    # If no cache files, just return a fresh one stamped for today
    if len(files) == 0:
        return f"cache/test_server_recordings_{today.isoformat()}.yaml"

    current_file = files[0]
    current_file_date = datetime.date.fromisoformat(
        re.findall(r"\d+-\d+-\d+", current_file)[0]
    )
    # Cache should be refreshed
    if (today - current_file_date).days > refresh_cache_days:
        # Delete old cache and return new file path
        os.remove(current_file)
        return f"cache/test_server_recordings_{today.isoformat()}.yaml"

    # Cache is still valid
    return current_file


def treasuremap_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the TreasureMap API are equivalent
    """

    # A request matches a TreasureMap request if the URI and method matches

    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def is_treasuremap_request(uri):
        patterns = {
            "delete": r"/api/v0/cancel_all/$",
            "submit": r"/api/v0/pointings/$",
        }
        for (submit_type, pattern) in patterns.items():
            if re.search(pattern, uri) is not None:
                return submit_type

        return False

    r1_is_treasuremap = is_treasuremap_request(r1_uri)
    r2_is_treasuremap = is_treasuremap_request(r2_uri)

    assert r1_is_treasuremap == r2_is_treasuremap and r1.method == r2.method


def lt_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the LT API are equivalent
    """

    # Check that the request modes are matching (should be either "request" or "abort")
    r1_request_mode = re.findall(
        r"mode=&quot;[a-zA-Z]+&quot;", r1.body.decode("utf-8")
    )[0]
    r2_request_mode = (
        re.findall(r"mode=&quot;[a-zA-Z]+&quot;", r2.body.decode("utf-8"))[0]
        if r2.body is not None
        else None
    )

    # For "request" calls, check that the "Device" parameters match up
    r1_device_matches = (
        re.findall(r"&lt;Device name=&quot;.+?&quot;", r1.body.decode("utf-8"))
        if r1.body is not None
        else []
    )
    r1_device = r1_device_matches[0] if (len(r1_device_matches) != 0) else None
    r2_device_matches = (
        re.findall(r"&lt;Device name=&quot;.+?&quot;", r2.body.decode("utf-8"))
        if r2.body is not None
        else []
    )
    r2_device = r2_device_matches[0] if (len(r2_device_matches) != 0) else None

    # A request matches an LT request if the URL matches, the POST/GET matches,
    # the mode ("request" or "abort") matches, and the instrument ("Device") matches.
    assert (
        r1.uri == r2.uri
        and r1.method == r2.method
        and r1_request_mode == r2_request_mode
        and r1_device == r2_device
    )


def lco_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the LCO API are equivalent
    """

    # A request matches an LCO request if the URI and method matches

    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def submit_type(uri):
        patterns = {
            "delete": r"/api/requestgroups/[0-9]+/cancel/$",
            "update": r"/api/requestgroups/[0-9]+/$",
            "submit": r"/api/requestgroups/$",
        }
        for (submit_type, pattern) in patterns.items():
            if re.search(pattern, uri) is not None:
                return submit_type

        return None

    r1_type = submit_type(r1_uri)
    r2_type = submit_type(r2_uri)

    assert r1_type == r2_type and r1.method == r2.method


def ztf_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the ZTF API are equivalent
    """

    # A request matches an ZTF request if the URI and method matches

    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def is_ztf_request(uri):
        pattern = r"/api/triggers/ztf"
        if re.search(pattern, uri) is not None:
            return True

        return False

    r1_is_ztf = is_ztf_request(r1_uri)
    r2_is_ztf = is_ztf_request(r2_uri)

    assert r1_is_ztf and r2_is_ztf and r1.method == r2.method


def swift_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the Swift API are equivalent
    """

    # A request matches a Swift request if the URI and method matches
    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def is_swift_request(uri):
        pattern = r"/toop/submit_json.php"
        if re.search(pattern, uri) is not None:
            return True

        return False

    r1_is_swift = is_swift_request(r1_uri)
    r2_is_swift = is_swift_request(r2_uri)

    assert r1_is_swift and r2_is_swift and r1.method == r2.method


def kait_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the KAIT API are equivalent
    """

    # A request matches a KAIT request if the URI and method matches

    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def is_kait_request(uri):
        pattern = r"/cgi-bin/internal/process_kait_ztf_request.py"
        if re.search(pattern, uri) is not None:
            return True

        return False

    r1_is_kait = is_kait_request(r1_uri)
    r2_is_kait = is_kait_request(r2_uri)

    assert r1_is_kait and r2_is_kait and r1.method == r2.method


def atlas_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the ATLAS API are equivalent
    """

    # A request matches an ATLAS request if the URI and method matches

    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def is_atlas_request(uri):
        pattern = r"/forcedphot/queue/"
        if re.search(pattern, uri) is not None:
            return True

        return False

    r1_is_atlas = is_atlas_request(r1_uri)
    r2_is_atlas = is_atlas_request(r2_uri)

    assert r1_is_atlas and r2_is_atlas and r1.method == r2.method


def ps1_request_matcher(r1, r2):
    """
    Helper function to help determine if two requests to the PS1 DR2 API are equivalent
    """

    # A request matches an PS1 request if the URI and method matches

    r1_uri = r1.uri.replace(":443", "")
    r2_uri = r2.uri.replace(":443", "")

    def is_ps1_request(uri):
        pattern = r"/api/v0.1/panstarrs"
        if re.search(pattern, uri) is not None:
            return True

        return False

    r1_is_ps1 = is_ps1_request(r1_uri)
    r2_is_ps1 = is_ps1_request(r2_uri)

    assert r1_is_ps1 and r2_is_ps1 and r1.method == r2.method


class TestRouteHandler(tornado.web.RequestHandler):
    """
    This handler intercepts calls coming from SkyPortal API handlers which make
    requests to external web services (like the LT telescope) and wraps them in a
    vcr context so that requests are cached and played back. The handler will forward
    the request to the approriate "real" host, cache the results, and pass them back
    to the SkyPortal test API server.
    """

    def delete(self):
        is_soap_action = "Soapaction" in self.request.headers
        if self.request.uri in [
            "/api/requestgroups/",
            "/api/triggers/ztf",
        ]:
            cache = get_cache_file_static()
        else:
            cache = get_cache_file()

        match_on = ['uri', 'method', 'body']
        if self.request.uri == "/node_agent2/node_agent":
            match_on = ["lt"]
        elif "/api/requestgroups/" in self.request.uri:
            match_on = ["lco"]
        elif self.request.uri == "/api/triggers/ztf":
            match_on = ["ztf"]
        elif self.request.uri == "/cgi-bin/internal/process_kait_ztf_request.py":
            match_on = ["kait"]

        with my_vcr.use_cassette(
            cache,
            record_mode="new_episodes",
            match_on=match_on,
        ) as cass:
            real_host = None
            for route in cfg["test_server.redirects"].keys():
                if re.match(route, self.request.uri):
                    real_host = cfg["test_server.redirects"][route]

            if real_host is not None:
                url = real_host + self.request.uri

                if is_soap_action:
                    log(f"Forwarding SOAP method call {url}")
                else:
                    log(f"Forwarding DELETE call {url}")

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    headers[k] = v

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    headers[k] = v

                if "/api/requestgroups/" in self.request.uri:
                    header = {'Authorization': headers['Authorization']}
                    json_body = (
                        json.loads(self.request.body.decode())
                        if len(self.request.body) > 0
                        else None
                    )
                    requests.delete(
                        url,
                        json=json_body,
                        headers=header,
                    )
                else:
                    log(f"Forwarding DELETE call: {url}")
                    s = requests.Session()
                    req = requests.Request(
                        'DELETE', url, data=self.request.body, headers=headers
                    )
                    prepped = req.prepare()
                    s.send(prepped)

                # Get recorded document and pass it back
                response = cass.responses_of(
                    vcr.request.Request("DELETE", url, self.request.body, headers)
                )[0]
                self.set_status(
                    response["status"]["code"], response["status"]["message"]
                )
                for k, v in response["headers"].items():
                    # The response from this test server will not be chunked even if
                    # the real response was
                    if not (k == "Transfer-Encoding" and "chunked" in v):
                        self.set_header(k, v[0])
                self.write(response["body"]["string"])

            else:
                self.set_status(500)
                self.write("Could not find test route redirect")

    def put(self):

        is_soap_action = "Soapaction" in self.request.headers
        if "/api/requestgroups/" in self.request.uri:
            cache = get_cache_file_static()
        elif self.request.uri == "/api/triggers/ztf":
            cache = get_cache_file_static()
        else:
            cache = get_cache_file()
        match_on = ['uri', 'method', 'body']
        if self.request.uri == "/node_agent2/node_agent":
            match_on = ["lt"]
        elif "/api/requestgroups/" in self.request.uri:
            match_on = ["lco"]
        elif self.request.uri == "/api/triggers/ztf":
            match_on = ["ztf"]
        elif self.request.uri == "/cgi-bin/internal/process_kait_ztf_request.py":
            match_on = ["kait"]

        with my_vcr.use_cassette(
            cache,
            record_mode="new_episodes",
            match_on=match_on,
        ) as cass:
            real_host = None
            for route in cfg["test_server.redirects"].keys():
                if re.match(route, self.request.uri):
                    real_host = cfg["test_server.redirects"][route]

            if real_host is not None:
                url = real_host + self.request.uri

                if is_soap_action:
                    log(f"Forwarding SOAP method call {url}")
                else:
                    log(f"Forwarding PUT call {url}")

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    headers[k] = v

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    headers[k] = v

                if "/api/requestgroups/" in self.request.uri:
                    header = {'Authorization': headers['Authorization']}
                    json_body = (
                        json.loads(self.request.body.decode())
                        if len(self.request.body) > 0
                        else None
                    )
                    requests.put(
                        url,
                        json=json_body,
                        headers=header,
                    )
                else:
                    log(f"Forwarding PUT call: {url}")
                    s = requests.Session()
                    req = requests.Request(
                        'PUT', url, data=self.request.body, headers=headers
                    )
                    prepped = req.prepare()
                    s.send(prepped)

                # Get recorded document and pass it back
                response = cass.responses_of(
                    vcr.request.Request("PUT", url, self.request.body, headers)
                )[0]
                self.set_status(
                    response["status"]["code"], response["status"]["message"]
                )
                for k, v in response["headers"].items():
                    # The response from this test server will not be chunked even if
                    # the real response was
                    if not (k == "Transfer-Encoding" and "chunked" in v):
                        self.set_header(k, v[0])
                self.write(response["body"]["string"])

            else:
                self.set_status(500)
                self.write("Could not find test route redirect")

    def get(self):

        is_wsdl = self.get_query_argument('wsdl', None)
        is_ps1 = re.match("/api/v0.1/panstarrs", self.request.uri)
        cached_urls = [
            "/api/requestgroups/",
            "/api/triggers/ztf",
            "/cgi-bin/internal/process_kait_ztf_request.py",
            "/forcedphot/queue/",
            "/api/v0.1/panstarrs",
        ]
        if any(re.match(pat, self.request.uri) for pat in cached_urls):
            cache = get_cache_file_static()
        else:
            cache = get_cache_file()

        with my_vcr.use_cassette(cache, record_mode="new_episodes") as cass:
            base_route = self.request.uri.split("?")[0]

            real_host = None
            for route in cfg["test_server.redirects"].keys():
                if re.match(route, base_route):
                    real_host = cfg["test_server.redirects"][route]

            if real_host is not None:
                url = real_host + self.request.uri

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    # Multiple values for a header should be in a comma-separated list
                    if k in headers:
                        headers[k] += f",{v}"
                    else:
                        headers[k] = str(v)

                if is_wsdl is not None:
                    log(f"Forwarding WSDL call {url}")
                    Client(url=url, headers=headers, cache=None)
                else:
                    log(f"Forwarding GET call: {url}")
                    if is_ps1:
                        # PS1 request does not need headers
                        requests.get(url)
                    else:
                        requests.get(url, headers=headers)

                # Get recorded document and pass it back
                response = cass.responses_of(
                    vcr.request.Request("GET", url, "", headers)
                )[0]
                print(response)
                self.set_status(
                    response["status"]["code"], response["status"]["message"]
                )
                for k, v in response["headers"].items():
                    # Content Length may change (for the SOAP call) as we overwrite the host
                    # in the response WSDL. Similarly, the response from this test server
                    # will not be chunked even if the real response was.
                    if k != "Content-Length" and not (
                        k == "Transfer-Encoding" and "chunked" in v
                    ):
                        self.set_header(k, v[0])

                if is_wsdl is not None:
                    # Override service location in the service definition
                    # so we can intercept the followup POST call
                    response_body = (
                        response["body"]["string"]
                        .decode("utf-8")
                        .replace(
                            real_host, f"http://localhost:{cfg['test_server.port']}"
                        )
                    )
                else:
                    response_body = response["body"]["string"]
                self.write(response_body)
            else:
                self.set_status(500)
                self.write("Could not find test route redirect")

    def post(self):

        cached_urls = [
            ".*/api/requestgroups/.*",
            ".*/toop/submit_json.php$",
            ".*/cgi-bin/internal/process_kait_ztf_request.py$",
            ".*/api/triggers/ztf/.*",
            ".*/node_agent2/node_agent/.*",
            ".*/forcedphot/queue/.*",
            ".*/api/v0/pointings/.*",
        ]
        is_soap_action = "Soapaction" in self.request.headers
        if any(re.match(pat, self.request.uri) for pat in cached_urls):
            cache = get_cache_file_static()
        else:
            cache = get_cache_file()
        match_on = ['uri', 'method', 'body']
        if self.request.uri == "/node_agent2/node_agent":
            match_on = ["lt"]
        elif self.request.uri == "/forcedphot/queue/":
            match_on = ["atlas"]
        elif "/api/requestgroups/" in self.request.uri:
            match_on = ["lco"]
        elif self.request.uri == "/api/triggers/ztf":
            match_on = ["ztf"]
        elif self.request.uri == "/cgi-bin/internal/process_kait_ztf_request.py":
            match_on = ["kait"]
        elif self.request.uri == "/api/v0/pointings":
            match_on = ["treasuremap"]
        elif "/toop/submit_json.php" in self.request.uri:
            match_on = ["swift"]

        with my_vcr.use_cassette(
            cache,
            record_mode="new_episodes",
            match_on=match_on,
        ) as cass:
            real_host = None
            for route in cfg["test_server.redirects"].keys():
                if re.match(route, self.request.uri):
                    real_host = cfg["test_server.redirects"][route]

            if real_host is not None:
                url = real_host + self.request.uri

                if is_soap_action:
                    log(f"Forwarding SOAP method call {url}")
                else:
                    log(f"Forwarding POST call {url}")

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    headers[k] = v

                if "/api/requestgroups/" in self.request.uri:
                    header = {'Authorization': headers['Authorization']}
                    json_body = (
                        json.loads(self.request.body.decode())
                        if len(self.request.body) > 0
                        else None
                    )
                    requests.post(
                        url,
                        json=json_body,
                        headers=header,
                    )
                elif "/forcedphot/queue/" in self.request.uri:
                    header = {
                        'Authorization': headers['Authorization'],
                        'Accept': 'application/json',
                    }
                    from urllib.parse import urlparse
                    from urllib.parse import parse_qs

                    url = f"{url}?{self.request.body.decode()}"
                    json_body = parse_qs(urlparse(url).query)

                    requests.post(url, data=json_body, headers=header)
                elif self.request.uri == "/api/v0/pointings":
                    json_body = (
                        json.loads(self.request.body.decode())
                        if len(self.request.body) > 0
                        else None
                    )
                    requests.post(url=url, json=json_body)
                else:
                    requests.post(url, data=self.request.body, headers=headers)

                response = cass.responses_of(
                    vcr.request.Request("POST", url, self.request.body, headers)
                )[0]

                self.set_status(
                    response["status"]["code"], response["status"]["message"]
                )
                for k, v in response["headers"].items():
                    # The response from this test server will not be chunked even if
                    # the real response was
                    if not (k == "Transfer-Encoding" and "chunked" in v):
                        self.set_header(k, v[0])
                self.write(response["body"]["string"])

            else:
                self.set_status(500)
                self.write("Could not find test route redirect")


def make_app():
    return tornado.web.Application(
        [
            (".*", TestRouteHandler),
        ]
    )


if __name__ == "__main__":
    env, cfg = load_env()
    log = make_log("testapiserver")
    my_vcr = vcr.VCR()
    my_vcr.register_matcher("atlas", atlas_request_matcher)
    my_vcr.register_matcher("lt", lt_request_matcher)
    my_vcr.register_matcher("lco", lco_request_matcher)
    my_vcr.register_matcher("ps1", ps1_request_matcher)
    my_vcr.register_matcher("ztf", ztf_request_matcher)
    my_vcr.register_matcher("kait", kait_request_matcher)
    my_vcr.register_matcher("treasuremap", treasuremap_request_matcher)
    my_vcr.register_matcher("swift", swift_request_matcher)
    if "test_server" in cfg:
        app = make_app()
        server = tornado.httpserver.HTTPServer(app)
        port = cfg["test_server.port"]
        server.listen(port)

        refresh_cache_days = cfg["test_server.refresh_cache_days"]

        log(f"Listening for test HTTP requests on port {port}")
        tornado.ioloop.IOLoop.current().start()
