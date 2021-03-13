from astropy.io import fits
from astropy.visualization import (
    MinMaxInterval,
    AsymmetricPercentileInterval,
    ZScaleInterval,
    AsinhStretch,
    LinearStretch,
    LogStretch,
    SqrtStretch,
    ImageNormalize,
)
import base64
import bson.json_util as bj
import gzip
import io
from marshmallow.exceptions import ValidationError
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pathlib
import requests
import tornado.escape
import traceback

from baselayer.app.access import auth_or_token
from baselayer.log import make_log
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    GroupStream,
    Obj,
    Stream,
    StreamUser,
    Source,
)
from .photometry import PhotometryHandler
from .thumbnail import ThumbnailHandler


log = make_log("alert")


s = requests.Session()


def make_thumbnail(a, ttype, ztftype):

    cutout_data = a[f"cutout{ztftype}"]["stampData"]
    with gzip.open(io.BytesIO(cutout_data), "rb") as f:
        with fits.open(io.BytesIO(f.read())) as hdu:
            # header = hdu[0].header
            data_flipped_y = np.flipud(hdu[0].data)
    # fixme: png, switch to fits eventually
    buff = io.BytesIO()
    plt.close("all")
    fig = plt.figure()
    fig.set_size_inches(4, 4, forward=False)
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    fig.add_axes(ax)

    # replace nans with median:
    img = np.array(data_flipped_y)
    # replace dubiously large values
    xl = np.greater(np.abs(img), 1e20, where=~np.isnan(img))
    if img[xl].any():
        img[xl] = np.nan
    if np.isnan(img).any():
        median = float(np.nanmean(img.flatten()))
        img = np.nan_to_num(img, nan=median)

    norm = ImageNormalize(
        img, stretch=LinearStretch() if ztftype == "Difference" else LogStretch()
    )
    img_norm = norm(img)
    normalizer = AsymmetricPercentileInterval(lower_percentile=1, upper_percentile=100)
    vmin, vmax = normalizer.get_limits(img_norm)
    ax.imshow(img_norm, cmap="bone", origin="lower", vmin=vmin, vmax=vmax)
    plt.savefig(buff, dpi=42)

    buff.seek(0)
    plt.close("all")

    thumb = {
        "obj_id": a["objectId"],
        "data": base64.b64encode(buff.read()).decode("utf-8"),
        "ttype": ttype,
    }

    return thumb


class ZTFAlertHandler(BaseHandler):
    def get_user_streams(self):

        streams = (
            DBSession()
            .query(Stream)
            .join(StreamUser)
            .filter(StreamUser.user_id == self.associated_user_object.id)
            .all()
        )
        if streams is None:
            streams = []

        return streams

    # async def query_kowalski(self, query: dict, timeout=7):
    #     base_url = f"{self.cfg['app.kowalski.protocol']}://" \
    #                f"{self.cfg['app.kowalski.host']}:{self.cfg['app.kowalski.port']}"
    #     headers = {"Authorization": f"Bearer {self.cfg['app.kowalski.token']}"}
    #
    #     resp = await c.fetch(
    #         os.path.join(base_url, 'api/queries'),
    #         method='POST',
    #         body=tornado.escape.json_encode(query),
    #         headers=headers,
    #         request_timeout=timeout
    #     )
    #
    #     return resp

    def query_kowalski(self, query: dict, timeout=7):
        base_url = (
            f"{self.cfg['app.kowalski.protocol']}://"
            f"{self.cfg['app.kowalski.host']}:{self.cfg['app.kowalski.port']}"
        )
        headers = {"Authorization": f"Bearer {self.cfg['app.kowalski.token']}"}

        resp = s.post(
            os.path.join(base_url, "api/queries"),
            json=query,
            headers=headers,
            timeout=timeout,
        )

        return resp

    @auth_or_token
    async def get(self, objectId: str = None):
        """
        ---
        single:
          description: Retrieve a ZTF objectId from Kowalski
          parameters:
            - in: path
              name: objectId
              required: true
              schema:
                type: str
            - in: query
              name: candid
              required: false
              schema:
                type: int
            - in: query
              name: includeAllFields
              required: false
              schema:
                type: boolean
          responses:
            200:
              description: retrieved alert(s)
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
            400:
              content:
                application/json:
                  schema: Error
        """
        streams = self.get_user_streams()

        # allow access to public data only by default
        selector = {1}

        for stream in streams:
            if "ztf" in stream.name.lower():
                selector.update(set(stream.altdata.get("selector", [])))

        selector = list(selector)

        include_all_fields = self.get_query_argument("includeAllFields", False)

        try:
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts",
                    "pipeline": [
                        {
                            "$match": {
                                "objectId": objectId,
                                "candidate.programid": {"$in": selector},
                            }
                        },
                        {
                            "$project": {
                                # grab only what's going to be rendered
                                "_id": 0,
                                "candid": {"$toString": "$candid"},  # js luvz bigints
                                "candidate.jd": 1,
                                "candidate.programid": 1,
                                "candidate.fid": 1,
                                "candidate.ra": 1,
                                "candidate.dec": 1,
                                "candidate.magpsf": 1,
                                "candidate.sigmapsf": 1,
                                "candidate.rb": 1,
                                "candidate.drb": 1,
                                "candidate.isdiffpos": 1,
                                "coordinates.l": 1,
                                "coordinates.b": 1,
                            }
                            if not include_all_fields
                            else {
                                "_id": 0,
                                "cutoutScience": 0,
                                "cutoutTemplate": 0,
                                "cutoutDifference": 0,
                            }
                        },
                    ],
                },
                # "kwargs": {
                #     "max_time_ms": 10000
                # }
            }

            candid = self.get_query_argument("candid", None)
            if candid:
                query["query"]["pipeline"][0]["$match"]["candid"] = int(candid)

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                alert_data = bj.loads(resp.text).get("data")
                return self.success(data=alert_data)
            else:
                return self.error(f"Failed to fetch data for {objectId} from Kowalski")

        except Exception:
            _err = traceback.format_exc()
            return self.error(f"failure: {_err}")

    @auth_or_token
    def post(self, objectId):
        """
        ---
        description: Save ZTF objectId from Kowalski as source in SkyPortal
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - type: object
                    properties:
                      candid:
                        type: integer
                        description: "alert candid to use to pull thumbnails. defaults to latest alert"
                        minimum: 1
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: "group ids to save source to. defaults to all user groups"
                        minItems: 1
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        streams = self.get_user_streams()
        obj_already_exists = Obj.query.get(objectId) is not None

        # allow access to public data only by default
        selector = {1}

        for stream in streams:
            if "ztf" in stream.name.lower():
                selector.update(set(stream.altdata.get("selector", [])))

        selector = list(selector)

        data = self.get_json()
        candid = data.get("candid", None)
        group_ids = data.pop("group_ids", None)

        try:
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts_aux",
                    "pipeline": [
                        {"$match": {"_id": objectId}},
                        {
                            "$project": {
                                "_id": 1,
                                "cross_matches": 1,
                                "prv_candidates": {
                                    "$filter": {
                                        "input": "$prv_candidates",
                                        "as": "item",
                                        "cond": {"$in": ["$$item.programid", selector]},
                                    }
                                },
                            }
                        },
                        {
                            "$project": {
                                "_id": 1,
                                "prv_candidates.magpsf": 1,
                                "prv_candidates.sigmapsf": 1,
                                "prv_candidates.diffmaglim": 1,
                                "prv_candidates.programid": 1,
                                "prv_candidates.fid": 1,
                                "prv_candidates.rb": 1,
                                "prv_candidates.ra": 1,
                                "prv_candidates.dec": 1,
                                "prv_candidates.candid": 1,
                                "prv_candidates.jd": 1,
                            }
                        },
                    ],
                },
            }

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                alert_data = bj.loads(resp.text).get("data")
                if len(alert_data) > 0:
                    alert_data = alert_data[0]
                else:
                    return self.error(f"{objectId} not found on Kowalski")
            else:
                return self.error(f"Failed to fetch data for {objectId} from Kowalski")

            # grab and append most recent candid as it may not be in prv_candidates
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts",
                    "pipeline": [
                        {
                            "$match": {
                                "objectId": objectId,
                                "candidate.programid": {"$in": selector},
                            }
                        },
                        {
                            "$project": {
                                # grab only what's going to be rendered
                                "_id": 0,
                                "candidate.candid": {"$toString": "$candidate.candid"},
                                "candidate.programid": 1,
                                "candidate.jd": 1,
                                "candidate.fid": 1,
                                "candidate.rb": 1,
                                "candidate.drb": 1,
                                "candidate.ra": 1,
                                "candidate.dec": 1,
                                "candidate.magpsf": 1,
                                "candidate.sigmapsf": 1,
                                "candidate.diffmaglim": 1,
                            }
                        },
                        {"$sort": {"candidate.jd": -1}},
                        {"$limit": 1},
                    ],
                },
            }

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                latest_alert_data = bj.loads(resp.text).get("data")
                if len(latest_alert_data) > 0:
                    latest_alert_data = latest_alert_data[0]
            else:
                return self.error(f"Failed to fetch data for {objectId} from Kowalski")

            if len(latest_alert_data) > 0:
                candids = {a.get("candid", None) for a in alert_data["prv_candidates"]}
                if latest_alert_data["candidate"]["candid"] not in candids:
                    alert_data["prv_candidates"].append(latest_alert_data["candidate"])

            df = pd.DataFrame.from_records(alert_data["prv_candidates"])
            mask_candid = df["candid"] == str(candid)

            if candid is None or sum(mask_candid) == 0:
                candid = int(latest_alert_data["candidate"]["candid"])
                alert = df.loc[df["candid"] == str(candid)].to_dict(orient="records")[0]
            else:
                alert = df.loc[mask_candid].to_dict(orient="records")[0]

            # post source
            drb = alert.get("drb")
            rb = alert.get("rb")
            score = drb if drb is not None and not np.isnan(drb) else rb
            alert_thin = {
                "id": objectId,
                "ra": alert.get("ra"),
                "dec": alert.get("dec"),
                "score": score,
                "altdata": {
                    "passing_alert_id": candid,
                },
            }

            schema = Obj.__schema__()
            # print(self.associated_user_object.groups)
            user_group_ids = [
                g.id
                for g in self.associated_user_object.groups
                if not g.single_user_group
            ]
            user_accessible_group_ids = [
                g.id for g in self.associated_user_object.accessible_groups
            ]
            if not user_group_ids:
                return self.error(
                    "You must belong to one or more groups before you can add sources."
                )
            if (group_ids is not None) and (
                len(set(group_ids) - set(user_accessible_group_ids)) > 0
            ):
                forbidden_groups = list(set(group_ids) - set(user_accessible_group_ids))
                return self.error(
                    "Insufficient group access permissions. Not a member of "
                    f"group IDs: {forbidden_groups}."
                )
            try:
                group_ids = [
                    int(_id)
                    for _id in group_ids
                    if int(_id) in user_accessible_group_ids
                ]
            except Exception:
                group_ids = user_group_ids
            if not group_ids:
                return self.error(
                    "Invalid group_ids field. Please specify at least "
                    "one valid group ID that you belong to."
                )
            try:
                obj = schema.load(alert_thin)
            except ValidationError as e:
                return self.error(
                    "Invalid/missing parameters: " f"{e.normalized_messages()}"
                )
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. Please specify at least "
                    "one valid group ID that you belong to."
                )

            DBSession().add(obj)
            DBSession().add_all(
                [
                    Source(
                        obj=obj,
                        group=group,
                        saved_by_id=self.associated_user_object.id,
                    )
                    for group in groups
                ]
            )
            DBSession().commit()
            if not obj_already_exists:
                obj.add_linked_thumbnails()

            # post photometry
            ztf_filters = {1: "ztfg", 2: "ztfr", 3: "ztfi"}
            df["ztf_filter"] = df["fid"].apply(lambda x: ztf_filters[x])
            df["magsys"] = "ab"
            df["mjd"] = df["jd"] - 2400000.5

            df["mjd"] = df["mjd"].apply(lambda x: np.float64(x))
            df["magpsf"] = df["magpsf"].apply(lambda x: np.float32(x))
            df["sigmapsf"] = df["sigmapsf"].apply(lambda x: np.float32(x))

            # deduplicate
            df = (
                df.drop_duplicates(subset=["mjd", "magpsf"])
                .reset_index(drop=True)
                .sort_values(by=["mjd"])
            )

            # filter out bad data:
            mask_good_diffmaglim = df["diffmaglim"] > 0
            df = df.loc[mask_good_diffmaglim]

            # get group stream access and map it to ZTF alert program ids
            group_stream_access = []
            for group in groups:
                group_streams = (
                    DBSession()
                    .query(Stream)
                    .join(GroupStream)
                    .filter(GroupStream.group_id == group.id)
                    .all()
                )
                if group_streams is None:
                    group_streams = []

                group_stream_selector = {1}

                for stream in group_streams:
                    if "ztf" in stream.name.lower():
                        group_stream_selector.update(
                            set(stream.altdata.get("selector", []))
                        )

                group_stream_access.append(
                    {"group_id": group.id, "permissions": list(group_stream_selector)}
                )

            # post data from different program_id's
            for pid in set(df.programid.unique()):
                group_ids = [
                    gsa.get("group_id")
                    for gsa in group_stream_access
                    if pid in gsa.get("permissions", [1])
                ]

                if len(group_ids) > 0:
                    pid_mask = df.programid == int(pid)

                    photometry = {
                        "obj_id": objectId,
                        "group_ids": group_ids,
                        "instrument_id": 1,  # placeholder
                        "mjd": df.loc[pid_mask, "mjd"].tolist(),
                        "mag": df.loc[pid_mask, "magpsf"].tolist(),
                        "magerr": df.loc[pid_mask, "sigmapsf"].tolist(),
                        "limiting_mag": df.loc[pid_mask, "diffmaglim"].tolist(),
                        "magsys": df.loc[pid_mask, "magsys"].tolist(),
                        "filter": df.loc[pid_mask, "ztf_filter"].tolist(),
                        "ra": df.loc[pid_mask, "ra"].tolist(),
                        "dec": df.loc[pid_mask, "dec"].tolist(),
                    }

                    if len(photometry.get("mag", ())) > 0:
                        photometry_handler = PhotometryHandler(
                            request=self.request, application=self.application
                        )
                        photometry_handler.request.body = tornado.escape.json_encode(
                            photometry
                        )
                        try:
                            photometry_handler.put()
                        except Exception:
                            log(
                                f"Failed to post photometry of {objectId} to group_ids {group_ids}"
                            )
                        # do not return anything yet
                        self.clear()

            # post cutouts
            for ttype, ztftype in [
                ("new", "Science"),
                ("ref", "Template"),
                ("sub", "Difference"),
            ]:
                query = {
                    "query_type": "find",
                    "query": {
                        "catalog": "ZTF_alerts",
                        "filter": {
                            "candid": candid,
                            "candidate.programid": {"$in": selector},
                        },
                        "projection": {"_id": 0, "objectId": 1, f"cutout{ztftype}": 1},
                    },
                    "kwargs": {
                        "limit": 1,
                    },
                }

                resp = self.query_kowalski(query=query)

                if resp.status_code == requests.codes.ok:
                    cutout = bj.loads(resp.text).get("data", list(dict()))[0]
                else:
                    cutout = dict()

                thumb = make_thumbnail(cutout, ttype, ztftype)

                try:
                    thumbnail_handler = ThumbnailHandler(
                        request=self.request, application=self.application
                    )
                    thumbnail_handler.request.body = tornado.escape.json_encode(thumb)
                    thumbnail_handler.post()
                except Exception as e:
                    log(f"Failed to post thumbnails of {objectId} | {candid}")
                    log(str(e))
                self.clear()

            self.push_all(action="skyportal/FETCH_SOURCES")
            self.push_all(action="skyportal/FETCH_RECENT_SOURCES")
            return self.success(data={"id": objectId})

        except Exception:
            _err = traceback.format_exc()
            return self.error(f"failure: {_err}")


class ZTFAlertAuxHandler(ZTFAlertHandler):
    @auth_or_token
    def get(self, objectId: str = None):
        """
        ---
        single:
          description: Retrieve aux data for an objectId from Kowalski
          parameters:
            - in: path
              name: objectId
              required: true
              schema:
                type: string
            - in: query
              name: includePrvCandidates
              required: false
              schema:
                type: boolean
            - in: query
              name: includeAllFields
              required: false
              schema:
                type: boolean
          responses:
            200:
              description: retrieval failed
              content:
                application/json:
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        """
        streams = self.get_user_streams()

        # allow access to public data only by default
        selector = {1}

        for stream in streams:
            if "ztf" in stream.name.lower():
                selector.update(set(stream.altdata.get("selector", [])))

        selector = list(selector)

        include_prv_candidates = self.get_query_argument("includePrvCandidates", "true")
        include_prv_candidates = (
            True if include_prv_candidates.lower() == "true" else False
        )
        include_all_fields = self.get_query_argument("includeAllFields", "false")
        include_all_fields = False if include_all_fields.lower() == "false" else True

        try:
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts_aux",
                    "pipeline": [
                        {"$match": {"_id": objectId}},
                        {
                            "$project": {
                                "_id": 1,
                                "cross_matches": 1,
                                "prv_candidates": {
                                    "$filter": {
                                        "input": "$prv_candidates",
                                        "as": "item",
                                        "cond": {"$in": ["$$item.programid", selector]},
                                    }
                                },
                            }
                        },
                    ],
                },
            }

            if not include_all_fields:
                query["query"]["pipeline"].append(
                    {
                        "$project": {
                            "_id": 1,
                            "cross_matches": 1,
                            "prv_candidates.magpsf": 1,
                            "prv_candidates.sigmapsf": 1,
                            "prv_candidates.diffmaglim": 1,
                            "prv_candidates.programid": 1,
                            "prv_candidates.fid": 1,
                            "prv_candidates.ra": 1,
                            "prv_candidates.dec": 1,
                            "prv_candidates.candid": 1,
                            "prv_candidates.jd": 1,
                        }
                    }
                )

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                alert_data = bj.loads(resp.text).get("data")
                if len(alert_data) > 0:
                    alert_data = alert_data[0]
                else:
                    # len = 0 means that objectId does not exists on Kowalski
                    self.set_status(404)
                    self.finish()
                    return
            else:
                return self.error(f"Failed to fetch data for {objectId} from Kowalski")

            # grab and append most recent candid as it should not be in prv_candidates
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts",
                    "pipeline": [
                        {
                            "$match": {
                                "objectId": objectId,
                                "candidate.programid": {"$in": selector},
                            }
                        },
                        {
                            "$project": {
                                # grab only what's going to be rendered
                                "_id": 0,
                                "candidate.candid": {"$toString": "$candidate.candid"},
                                "candidate.programid": 1,
                                "candidate.jd": 1,
                                "candidate.fid": 1,
                                "candidate.ra": 1,
                                "candidate.dec": 1,
                                "candidate.magpsf": 1,
                                "candidate.sigmapsf": 1,
                                "candidate.diffmaglim": 1,
                                "coordinates.l": 1,
                                "coordinates.b": 1,
                            }
                            if not include_all_fields
                            else {
                                "_id": 0,
                                "cutoutScience": 0,
                                "cutoutTemplate": 0,
                                "cutoutDifference": 0,
                            }
                        },
                        {"$sort": {"candidate.jd": -1}},
                        {"$limit": 1},
                    ],
                },
            }

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                latest_alert_data = bj.loads(resp.text).get("data", list(dict()))
                if len(latest_alert_data) > 0:
                    latest_alert_data = latest_alert_data[0]
                else:
                    # len = 0 means that user has insufficient permissions to see objectId
                    self.set_status(404)
                    self.finish()
                    return
            else:
                return self.error(f"Failed to fetch data for {objectId} from Kowalski")

            candids = {a.get("candid", None) for a in alert_data["prv_candidates"]}
            if latest_alert_data["candidate"]["candid"] not in candids:
                alert_data["prv_candidates"].append(latest_alert_data["candidate"])

            # cross-match with the TNS
            rads = np.array(
                [
                    candid["ra"]
                    for candid in alert_data["prv_candidates"]
                    if candid.get("ra") is not None
                ]
            )
            decs = np.array(
                [
                    candid["dec"]
                    for candid in alert_data["prv_candidates"]
                    if candid.get("dec") is not None
                ]
            )

            ra = np.median(np.unique(rads.round(decimals=10)))
            dec = np.median(np.unique(decs.round(decimals=10)))
            # save median coordinates
            alert_data["coordinates"] = {
                "ra_median": ra,
                "dec_median": dec,
            }
            query = {
                "query_type": "cone_search",
                "query": {
                    "object_coordinates": {
                        "cone_search_radius": 2,
                        "cone_search_unit": "arcsec",
                        "radec": {objectId: [ra, dec]},
                    },
                    "catalogs": {
                        "TNS": {
                            "filter": {},
                            "projection": {
                                "name": 1,
                                "_id": 1,
                                "disc__instrument/s": 1,
                                "disc__internal_name": 1,
                                "discovery_data_source/s": 1,
                                "discovery_date_(ut)": 1,
                                "discovery_filter": 1,
                                "discovery_mag/flux": 1,
                                "reporting_group/s": 1,
                                "associated_group/s": 1,
                                "public": 1,
                            },
                        }
                    },
                },
                "kwargs": {"filter_first": False},
            }

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                tns_data = bj.loads(resp.text).get("data").get("TNS").get(objectId)
                alert_data["cross_matches"]["TNS"] = tns_data

            if not include_prv_candidates:
                alert_data.pop("prv_candidates", None)

            return self.success(data=alert_data)

        except Exception:
            _err = traceback.format_exc()
            return self.error(_err)


class ZTFAlertCutoutHandler(ZTFAlertHandler):
    @auth_or_token
    async def get(self, objectId: str = None):
        """
        ---
        summary: Serve ZTF alert cutout as fits or png
        tags:
          - lab

        parameters:
          - in: query
            name: candid
            description: "ZTF alert candid"
            required: true
            schema:
              type: integer
          - in: query
            name: cutout
            description: "retrieve science, template, or difference cutout image?"
            required: true
            schema:
              type: string
              enum: [science, template, difference]
          - in: query
            name: file_format
            description: "response file format: original loss-less FITS or rendered png"
            required: true
            schema:
              type: string
              enum: [fits, png]
          - in: query
            name: interval
            description: "Interval to use when rendering png"
            required: false
            schema:
              type: string
              enum: [min_max, zscale]
          - in: query
            name: stretch
            description: "Stretch to use when rendering png"
            required: false
            schema:
              type: string
              enum: [linear, log, asinh, sqrt]
          - in: query
            name: cmap
            description: "Color map to use when rendering png"
            required: false
            schema:
              type: string
              enum: [bone, gray, cividis, viridis, magma]

        responses:
          '200':
            description: retrieved cutout
            content:
              image/fits:
                schema:
                  type: string
                  format: binary
              image/png:
                schema:
                  type: string
                  format: binary

          '400':
            description: retrieval failed
            content:
              application/json:
                schema: Error
        """
        streams = self.get_user_streams()

        # allow access to public data only by default
        selector = {1}

        for stream in streams:
            if "ztf" in stream.name.lower():
                selector.update(set(stream.altdata.get("selector", [])))

        selector = list(selector)

        try:
            candid = int(self.get_argument("candid"))
            cutout = self.get_argument("cutout").capitalize()
            file_format = self.get_argument("file_format").lower()
            interval = self.get_argument("interval", default=None)
            stretch = self.get_argument("stretch", default=None)
            cmap = self.get_argument("cmap", default=None)

            known_cutouts = ["Science", "Template", "Difference"]
            if cutout not in known_cutouts:
                return self.error(
                    f"cutout {cutout} of {objectId}/{candid} not in {str(known_cutouts)}"
                )
            known_file_formats = ["fits", "png"]
            if file_format not in known_file_formats:
                return self.error(
                    f"file format {file_format} of {objectId}/{candid}/{cutout} not in {str(known_file_formats)}"
                )

            normalization_methods = {
                "asymmetric_percentile": AsymmetricPercentileInterval(
                    lower_percentile=1, upper_percentile=100
                ),
                "min_max": MinMaxInterval(),
                "zscale": ZScaleInterval(nsamples=600, contrast=0.045, krej=2.5),
            }
            if interval is None:
                interval = "asymmetric_percentile"
            normalizer = normalization_methods.get(
                interval.lower(),
                AsymmetricPercentileInterval(lower_percentile=1, upper_percentile=100),
            )

            stretching_methods = {
                "linear": LinearStretch,
                "log": LogStretch,
                "asinh": AsinhStretch,
                "sqrt": SqrtStretch,
            }
            if stretch is None:
                stretch = "log" if cutout != "Difference" else "linear"
            stretcher = stretching_methods.get(stretch.lower(), LogStretch)()

            if (cmap is None) or (
                cmap.lower() not in ["bone", "gray", "cividis", "viridis", "magma"]
            ):
                cmap = "bone"
            else:
                cmap = cmap.lower()

            query = {
                "query_type": "find",
                "query": {
                    "catalog": "ZTF_alerts",
                    "filter": {
                        "candid": candid,
                        "candidate.programid": {"$in": selector},
                    },
                    "projection": {"_id": 0, f"cutout{cutout}": 1},
                },
                "kwargs": {"limit": 1, "max_time_ms": 5000},
            }

            resp = self.query_kowalski(query=query)

            if resp.status_code == requests.codes.ok:
                alert = bj.loads(resp.text).get("data", list(dict()))[0]
            else:
                alert = dict()

            cutout_data = bj.loads(bj.dumps([alert[f"cutout{cutout}"]["stampData"]]))[0]

            # unzipped fits name
            fits_name = pathlib.Path(alert[f"cutout{cutout}"]["fileName"]).with_suffix(
                ""
            )

            # unzip and flip about y axis on the server side
            with gzip.open(io.BytesIO(cutout_data), "rb") as f:
                with fits.open(io.BytesIO(f.read())) as hdu:
                    header = hdu[0].header
                    data_flipped_y = np.flipud(hdu[0].data)

            if file_format == "fits":
                hdu = fits.PrimaryHDU(data_flipped_y, header=header)
                hdul = fits.HDUList([hdu])

                stamp_fits = io.BytesIO()
                hdul.writeto(fileobj=stamp_fits)

                self.set_header("Content-Type", "image/fits")
                self.set_header(
                    "Content-Disposition", f"Attachment;filename={fits_name}"
                )
                self.write(stamp_fits.getvalue())

            if file_format == "png":
                buff = io.BytesIO()
                plt.close("all")

                fig, ax = plt.subplots(figsize=(4, 4))
                fig.subplots_adjust(0, 0, 1, 1)
                ax.set_axis_off()

                # replace nans with median:
                img = np.array(data_flipped_y)
                # replace dubiously large values
                xl = np.greater(np.abs(img), 1e20, where=~np.isnan(img))
                if img[xl].any():
                    img[xl] = np.nan
                if np.isnan(img).any():
                    median = float(np.nanmean(img.flatten()))
                    img = np.nan_to_num(img, nan=median)
                norm = ImageNormalize(img, stretch=stretcher)
                img_norm = norm(img)
                vmin, vmax = normalizer.get_limits(img_norm)
                ax.imshow(img_norm, cmap=cmap, origin="lower", vmin=vmin, vmax=vmax)
                plt.savefig(buff, dpi=42)
                buff.seek(0)
                plt.close("all")
                self.set_header("Content-Type", "image/png")
                self.write(buff.getvalue())

        except Exception:
            _err = traceback.format_exc()
            return self.error(f"failure: {_err}")
