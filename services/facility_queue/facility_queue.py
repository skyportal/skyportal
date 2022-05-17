# For Michael, an example test run with Curl:
#
# curl -X POST http://localhost:64510 -d '{"method": "GET", "endpoint": "http://localhost:9980"}'
#

import tornado.ioloop
import tornado.web
import asyncio
from tornado.ioloop import IOLoop
import tornado.escape
import json


from baselayer.app.env import load_env

env, cfg = load_env()


class FacilityTransactionRequest:
    def __init__(self, method=None, endpoint=None, headers=None):
        self.method = method
        self.endpoint = endpoint
        self.headers = headers


class FacilityQueue(asyncio.Queue):
    async def load_from_db(self):
        # Load items from database into queue

        # Dummy examples:
        await self.put(
            FacilityTransactionRequest(
                method='PUT', endpoint='http://localhost:9999', headers={'auth': None}
            )
        )
        await self.put(
            FacilityTransactionRequest(
                method='GET', endpoint='http://localhost:9999', headers={'auth': '123'}
            )
        )

    async def service(self):
        while True:
            req = await queue.get()
            print(f"{req.method} request to [{req.endpoint}]")

            # Simulate time taken to service this request
            await asyncio.sleep(3)

            print(f"{req.method} request to [{req.endpoint}] completed")


queue = FacilityQueue()


class QueueHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write({"status": "success", "data": {"queue_length": queue.qsize()}})

    async def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            return self.write({"status": "error", "message": "Malformed JSON data"})

        # validate data here and return 400 if invalid
        try:
            req = FacilityTransactionRequest(**data)
        except TypeError:
            self.set_status(400)
            return self.write(
                {
                    "status": "error",
                    "message": "Invalid arguments; cannot construct facility request",
                }
            )

        for field in ('method', 'endpoint'):
            if getattr(req, field) is None:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"Missing request attribute `{field}`",
                    }
                )

        await queue.put(req)

        self.write(
            {
                "status": "success",
                "message": "Facility request accepted into queue",
                "data": {"queue_length": queue.qsize()},
            }
        )


if __name__ == "__main__":
    app = tornado.web.Application([(r"/", QueueHandler)])
    app.listen(cfg["ports.facility_queue"])

    loop = IOLoop.current()
    loop.add_callback(queue.load_from_db)
    loop.add_callback(queue.service)
    loop.start()
