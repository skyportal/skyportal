import uuid

import vcr

import tornado.web
import tornado.wsgi
from tornado.web import RequestHandler

# from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import ServiceBase

# from spyne.server.wsgi import WsgiApplication
from spyne.model.primitive import String

# from spyne.protocol.soap import Soap11

from lxml import etree

from suds import Client
import requests

from baselayer.log import make_log
from baselayer.app.env import load_env

env, cfg = load_env()
log = make_log("testserver")


class LTService(ServiceBase):
    """
    This is a mock LT server for LT Telescope API follow-up tests
    """

    @srpc(String, _returns=String)
    def handle_rtml(name):
        # Build mock success response
        log("External Service: received")
        response = etree.Element("RTML", mode="confirm", uid=str(uuid.uuid4()))
        return etree.tostring(
            response, doctype='<?xml version="1.0" encoding="ISO-8859-1"?>'
        )


class TestRouteHandler(RequestHandler):
    """
    This is a simple example REST API service to be included
    in the example test server.
    """

    def get(self):
        log("Get!")
        log(self.request.uri)
        is_wsdl = self.get_query_argument('wsdl', None)
        if is_wsdl is not None:
            log("Intercepting a WSDL call")
            with vcr.use_cassette(
                'cache/test_server_recordings.yaml', record_mode="new_episodes"
            ) as cass:
                base_route = self.request.uri.split("?")[0]
                real_host = cfg["test_server.redirects"][base_route]
                url = real_host + self.request.uri

                # Convert Tornado HTTPHeaders object to a regular dict
                headers = {}
                for k, v in self.request.headers.get_all():
                    if k in headers:
                        headers[k].append(v)
                    else:
                        headers[k] = [v]

                Client(url=url, headers=headers, cache=None)

                # Get recorded document
                response = cass.responses_of(
                    vcr.request.Request("GET", url, "", headers)
                )[0]
                self.set_status(
                    response["status"]["code"], response["status"]["message"]
                )
                for k, v in response["headers"].items():
                    if k != "Content-Length":
                        self.set_header(k, v[0])

                # Override service location so we can intercept the followup POST call
                response_body = (
                    response["body"]["string"]
                    .decode("utf-8")
                    .replace(real_host, f"http://localhost:{cfg['ports.test_server']}")
                )
                self.write(response_body)
        else:
            self.set_status(200)
            self.write("Hello from REST server!")

    def post(self):
        log("Post!")
        log(self.request.uri)
        is_soap_action = "Soapaction" in self.request.headers
        if is_soap_action is not None:
            log("Intercepting a SOAP action call")

        with vcr.use_cassette(
            'cache/test_server_recordings.yaml',
            record_mode="new_episodes",
            match_on=['uri', 'method', 'body'],
        ) as cass:
            url = "http://localhost:64503" + self.request.uri

            # Convert Tornado HTTPHeaders object to a regular dict
            headers = {}
            for k, v in self.request.headers.get_all():
                headers[k] = v

            requests.post(url, data=self.request.body, headers=headers)
            log("Posted to real server! Trying to get record now")
            # Get recorded document
            response = cass.responses_of(
                vcr.request.Request("POST", url, self.request.body, headers)
            )[0]
            self.set_status(response["status"]["code"], response["status"]["message"])
            for k, v in response["headers"].items():
                self.set_header(k, v[0])
            self.write(response["body"]["string"])


def make_app():
    # app = Application(
    #     [LTService],
    #     "mock_soap_server.http",
    #     in_protocol=Soap11(validator="lxml"),
    #     out_protocol=Soap11(),
    # )
    # wsgi_app = tornado.wsgi.WSGIContainer(WsgiApplication(app))
    return tornado.web.Application(
        [
            (".*", TestRouteHandler),
            # (
            #     "/node_agent2/node_agent",
            #     tornado.web.FallbackHandler,
            #     dict(fallback=wsgi_app),
            # ),
        ]
    )
