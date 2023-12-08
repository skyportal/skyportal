from threading import Thread
import time

import tornado.ioloop
import tornado.web
import asyncio
import tornado.escape
import json

import sqlalchemy as sa

from baselayer.app.models import init_db
from baselayer.app.env import load_env
from baselayer.log import make_log
from baselayer.app.flow import Flow

from skyportal.models import (
    ThreadSession,
    Obj,
)

env, cfg = load_env()
log = make_log('thumbnail_queue')

init_db(**cfg['database'])

queue = []


def service(queue):

    while True:
        with ThreadSession() as session:
            try:
                if len(queue) == 0:
                    time.sleep(1)
                    continue
                data = queue.pop(0)
                if data is None:
                    continue

                obj_ids = data.get("obj_ids")
                for obj_id in obj_ids:
                    obj = session.scalars(
                        sa.select(Obj).where(Obj.id == obj_id)
                    ).first()
                    if obj is None:
                        log(f"Source {obj_id} not found")
                        continue

                    existing_thumbnail_types = [thumb.type for thumb in obj.thumbnails]
                    thumbnails = list(
                        {"ps1", "ls", "sdss"} - set(existing_thumbnail_types)
                    )
                    if len(thumbnails) == 0:
                        log(f"Source {obj_id} has all thumbnails.")
                        continue

                    obj.add_linked_thumbnails(thumbnails, session)

                    flow = Flow()
                    flow.push(
                        '*',
                        "skyportal/REFRESH_SOURCE",
                        payload={"obj_key": obj.internal_key},
                    )
                    flow.push(
                        '*',
                        "skyportal/REFRESH_CANDIDATE",
                        payload={"id": obj.internal_key},
                    )

            except Exception as e:
                session.rollback()
                log(f"Error processing thumbnail request for object {obj_id}: {str(e)}")


def api(queue):
    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write({"status": "success", "data": {"queue_length": len(queue)}})

        async def post(self):

            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})

            required_keys = {'obj_ids'}
            if not required_keys.issubset(set(data.keys())):
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": "thumbnail requests require obj_ids",
                    }
                )

            queue.append(data)

            self.set_status(200)
            return self.write(
                {
                    "status": "success",
                    "message": "thumbnail request accepted into queue",
                    "data": {"queue_length": len(queue)},
                }
            )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.thumbnail_queue"])
    loop.run_forever()


if __name__ == "__main__":
    try:
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log(f"Current thumbnail queue length: {len(queue)}")
            time.sleep(60)
    except Exception as e:
        log(f"Error starting thumbnail queue: {str(e)}")
        raise e
