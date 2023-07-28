import asyncio
import io
import json
import re
import time
import traceback
from threading import Thread

import pandas as pd
import requests
import sqlalchemy as sa
import tornado.escape
import tornado.ioloop
import tornado.web
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.thumbnail import post_thumbnail
from skyportal.models import DBSession, Obj
from skyportal.utils.thumbnail import make_thumbnail

env, cfg = load_env()
log = make_log('thumbnail_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

queue = []

thumbnail_types = {
    "sci": "Science",
    "ref": "Reference",
    "diff": "Difference",
}


def service(queue):

    while True:
        with DBSession() as session:
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

                    try:
                        if not re.match(r"ZTF\d{2}[a-z]{7}", obj_id):
                            # we'll grab a science image from IPAC
                            ra, dec = obj.ra, obj.dec
                            url = f"https://irsa.ipac.caltech.edu/ibe/search/ztf/products/sci?POS={ra},{dec}&mcen&ct=csv"
                            r = requests.get(url)
                            if r.status_code != 200:
                                log(f"Failed to fetch cutout for {obj_id} from IPAC")
                                continue

                            df = pd.read_csv(io.BytesIO(r.content))

                            meta = df.iloc[0].to_dict()
                            # the url will look like 'https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/'+year+'/'+month+day+'/'+fracday+'/ztf_'+filefracday+'_'+paddedfield+'_'+filtercode+'_c'+paddedccdid+'_'+imgtypecode+'_q'+qid+'_'+suffix
                            year = str(meta["filefracday"])[:4]
                            month_day = str(meta["filefracday"])[4:8]
                            fracday = str(meta["filefracday"])[8:]
                            padded_field = str(meta["field"]).zfill(6)
                            padded_ccdid = str(meta["ccdid"]).zfill(2)
                            cutout_url = f"https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/{year}/{month_day}/{fracday}/ztf_{meta['filefracday']}_{padded_field}_{meta['filtercode']}_c{padded_ccdid}_{meta['imgtypecode']}_q{meta['qid']}_sciimg.fits"

                            # we want a (63,63) image centered on the object
                            cutout_url += f"?center={ra},{dec}&size=63arcsec"

                            r = requests.get(cutout_url)
                            if r.status_code != 200:
                                log(r.content)
                                log(f"Failed to fetch cutout for {obj_id} from IPAC")
                                continue
                            a = {
                                "cutoutScience": {
                                    "stampData": r.content,
                                },
                                "objectId": obj_id,
                            }
                            thumb = make_thumbnail(a, "ztf", "Science")
                            if thumb is not None:
                                post_thumbnail(thumb, 1, session)
                    except Exception as e:
                        log(f"Error fetching cutout for {obj_id} from IPAC: {str(e)}")
                        traceback.print_exc()

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
