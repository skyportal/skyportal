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
import pandas as pd
import pathlib
from penquins import Kowalski
import tornado.escape
import traceback

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    GroupStream,
    Obj,
    Stream,
    Source,
)
from .photometry import PhotometryHandler
from .thumbnail import ThumbnailHandler


env, cfg = load_env()
log = make_log("alert")


kowalski = None
if cfg.get('app.kowalski.enabled', False):
    try:
        kowalski = Kowalski(
            token=cfg["app.kowalski.token"],
            protocol=cfg["app.kowalski.protocol"],
            host=cfg["app.kowalski.host"],
            port=int(cfg["app.kowalski.port"]),
            timeout=10,
        )
        connection_ok = kowalski.ping()
        log(f"Kowalski connection OK: {connection_ok}")
        if not connection_ok:
            kowalski = None
    except Exception as e:
        log(f"Kowalski connection failed: {str(e)}")
        kowalski = None


INSTRUMENTS = {"ZTF"}


def make_thumbnail(a, ttype, ztftype):

    cutout_data = a[f"cutout{ztftype}"]["stampData"]
    with gzip.open(io.BytesIO(cutout_data), "rb") as f:
        with fits.open(io.BytesIO(f.read()), ignore_missing_simple=True) as hdu:
            # header = hdu[0].header
            data_flipped_y = np.flipud(hdu[0].data)
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


class AlertHandler(BaseHandler):
    @auth_or_token
    async def get(self, object_id: str = None):
        """
        ---
        single:
          description: Retrieve an object from Kowalski by objectId
          tags:
            - alerts
            - kowalski
          parameters:
            - in: path
              name: object_id
              required: true
              schema:
                type: str
            - in: query
              name: instrument
              required: false
              default: 'ZTF'
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
        multiple:
          description: Retrieve objects from Kowalski by objectId and or position
          tags:
            - alerts
            - kowalski
          parameters:
            - in: query
              name: objectId
              required: false
              schema:
                type: str
              description: can be a single objectId or a comma-separated list of objectIds
            - in: query
              name: instrument
              required: false
              default: 'ZTF'
              schema:
                type: str
            - in: query
              name: ra
              required: false
              schema:
                type: float
              description: RA in degrees
            - in: query
              name: dec
              required: false
              schema:
                type: float
              description: Dec. in degrees
            - in: query
              name: radius
              required: false
              schema:
                type: float
              description: Max distance from specified (RA, Dec) (capped at 1 deg)
            - in: query
              name: radius_units
              required: false
              schema:
                type: string
              description: Distance units (either "deg", "arcmin", or "arcsec")
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
                      - type: object
                        properties:
                          data:
                            type: array
                            items:
                              type: object
            400:
              content:
                application/json:
                  schema: Error
        """
        # allow access to public data only by default
        program_id_selector = {1}

        # using self.Session() should attach the
        # associated_user_object to the current session
        # so it can lazy load things like streams
        with self.Session():
            for stream in self.associated_user_object.streams:
                if "ztf" in stream.name.lower():
                    program_id_selector.update(set(stream.altdata.get("selector", [])))

        program_id_selector = list(program_id_selector)

        instrument = self.get_query_argument("instrument", "ZTF").upper()
        if instrument not in INSTRUMENTS:
            raise ValueError("Instrument name not recognised")

        default_projection = {
            "_id": 0,
            "objectId": 1,
            "candid": {"$toString": "$candid"},
            "candidate.ra": 1,
            "candidate.dec": 1,
            "candidate.jd": 1,
            "candidate.fid": 1,
            "candidate.magpsf": 1,
            "candidate.sigmapsf": 1,
            "candidate.isdiffpos": 1,
            "candidate.rb": 1,
            "candidate.drb": 1,
            "candidate.programid": 1,
            "classifications": 1,
            "coordinates.l": 1,
            "coordinates.b": 1,
        }

        include_all_fields = self.get_query_argument("includeAllFields", False)

        if object_id is not None:
            # grabbing alerts by single objectId
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts",
                    "pipeline": [
                        {
                            "$match": {
                                "objectId": object_id,
                                "candidate.programid": {"$in": program_id_selector},
                            }
                        },
                        {
                            "$project": default_projection
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
                "kwargs": {"max_time_ms": 10000},
            }

            candid = self.get_query_argument("candid", None)
            if candid is not None:
                query["query"]["pipeline"][0]["$match"]["candid"] = int(candid)

            response = kowalski.query(query=query)

            if response.get("status", "error") == "success":
                alert_data = response.get("data")
                return self.success(data=alert_data)
            else:
                return self.error(f"Failed to fetch data for {object_id} from Kowalski")

        # executing a general search
        object_ids = self.get_query_argument(
            "objectId", None
        )  # could be a comma-separated list
        ra = self.get_query_argument("ra", None)
        dec = self.get_query_argument("dec", None)
        radius = self.get_query_argument("radius", None)
        radius_units = self.get_query_argument("radius_units", None)

        position_tuple = (ra, dec, radius, radius_units)

        if not any((object_ids, ra, dec, radius, radius_units)):
            return self.error("Missing required parameters")

        if not all(position_tuple) and any(position_tuple):
            # incomplete positional arguments? throw errors, since
            # either all or none should be provided
            if ra is None:
                return self.error("Missing required parameter: ra")
            if dec is None:
                return self.error("Missing required parameter: dec")
            if radius is None:
                return self.error("Missing required parameter: radius")
            if radius_units is None:
                return self.error("Missing required parameter: radius_units")
        if all(position_tuple):
            # complete positional arguments? run "near" query
            if radius_units not in ["deg", "arcmin", "arcsec"]:
                return self.error(
                    "Invalid radius_units value. Must be one of either "
                    "'deg', 'arcmin', or 'arcsec'."
                )
            try:
                ra = float(ra)
                dec = float(dec)
                radius = float(radius)
            except ValueError:
                return self.error("Invalid (non-float) value provided.")
            if (
                (radius_units == "deg" and radius > 1)
                or (radius_units == "arcmin" and radius > 60)
                or (radius_units == "arcsec" and radius > 3600)
            ):
                return self.error("Radius must be <= 1.0 deg")

            query = {
                "query_type": "near",
                "query": {
                    "max_distance": radius,
                    "distance_units": radius_units,
                    "radec": {"query_coords": [ra, dec]},
                    "catalogs": {
                        "ZTF_alerts": {
                            "filter": {
                                "candidate.programid": {"$in": program_id_selector},
                            },
                            "projection": default_projection
                            if not include_all_fields
                            else {
                                "_id": 0,
                                "cutoutScience": 0,
                                "cutoutTemplate": 0,
                                "cutoutDifference": 0,
                            },
                        }
                    },
                },
                "kwargs": {
                    "max_time_ms": 10000,
                    "limit": 10000,
                },
            }

            # additional filters?
            if object_ids is not None:
                query["query"]["catalogs"]["ZTF_alerts"]["filter"]["objectId"] = {
                    "$in": [oid.strip() for oid in object_ids.split(",")]
                }

            response = kowalski.query(query=query)

            if response.get("status", "error") == "success":
                alert_data = response.get("data")
                return self.success(data=alert_data["ZTF_alerts"]["query_coords"])

            return self.error(response.get("message"))

        # otherwise, run a find query with the specified filter
        query = {
            "query_type": "find",
            "query": {
                "catalog": "ZTF_alerts",
                "filter": {
                    "objectId": {"$in": [oid.strip() for oid in object_ids.split(",")]},
                    "candidate.programid": {"$in": program_id_selector},
                },
                "projection": default_projection
                if not include_all_fields
                else {
                    "_id": 0,
                    "cutoutScience": 0,
                    "cutoutTemplate": 0,
                    "cutoutDifference": 0,
                },
            },
            "kwargs": {
                "max_time_ms": 10000,
                "limit": 10000,
            },
        }

        response = kowalski.query(query=query)

        if response.get("status", "error") == "success":
            alert_data = response.get("data")
            return self.success(data=alert_data)

        return self.error(response.get("message"))

    @permissions(["Upload data"])
    def post(self, objectId):
        """
        ---
        description: Save ZTF objectId from Kowalski as source in SkyPortal
        tags:
          - alerts
          - kowalski
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  candid:
                    type: integer
                    description: Alert candid to use to pull thumbnails. Defaults to latest alert
                    minimum: 1
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      Group IDs to save source to. Can alternatively be the string
                      'all' to save to all of requesting user's groups.
                    minItems: 1
                required:
                  - group_ids
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
        obj_already_exists = (
            Obj.get_if_accessible_by(objectId, self.current_user) is not None
        )

        # allow access to public data only by default
        program_id_selector = {1}

        with self.Session():
            for stream in self.associated_user_object.streams:
                if "ztf" in stream.name.lower():
                    program_id_selector.update(set(stream.altdata.get("selector", [])))

        program_id_selector = list(program_id_selector)

        data = self.get_json()
        candid = data.get("candid", None)
        group_ids = data.pop("group_ids", None)
        if group_ids is None:
            return self.error("Missing required `group_ids` parameter.")

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
                                        "cond": {
                                            "$in": [
                                                "$$item.programid",
                                                program_id_selector,
                                            ]
                                        },
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

            response = kowalski.query(query=query)
            if response.get("status", "error") == "success":
                alert_data = response.get("data")
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
                                "candidate.programid": {"$in": program_id_selector},
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

            response = kowalski.query(query=query)
            if response.get("status", "error") == "success":
                latest_alert_data = response.get("data")
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
            if not isinstance(group_ids, list) and group_ids != "all":
                return self.error(
                    "Invalid parameter value: group_ids must be a list of integers or the string 'all'"
                )
            if group_ids == "all":
                group_ids = user_group_ids
            if len(group_ids) == 0:
                return self.error(
                    "Invalid group_ids field. Please specify at least "
                    "one valid group ID that you belong to."
                )
            try:
                group_ids = [int(_id) for _id in group_ids]
            except ValueError:
                return self.error(
                    "Invalid group_ids parameter: all elements must be integers."
                )
            forbidden_groups = list(set(group_ids) - set(user_accessible_group_ids))
            if len(forbidden_groups) > 0:
                return self.error(
                    "Insufficient group access permissions. Not a member of "
                    f"group IDs: {forbidden_groups}."
                )
            try:
                obj = schema.load(alert_thin)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )
            groups = Group.get_if_accessible_by(group_ids, self.current_user)
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
            self.verify_and_commit()
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
                group_stream_subquery = (
                    GroupStream.query_records_accessible_by(self.current_user)
                    .filter(GroupStream.group_id == group.id)
                    .subquery()
                )
                group_streams = (
                    Stream.query_records_accessible_by(self.current_user)
                    .join(
                        group_stream_subquery,
                        Stream.id == group_stream_subquery.c.stream_id,
                    )
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
                            "candidate.programid": {"$in": program_id_selector},
                        },
                        "projection": {"_id": 0, "objectId": 1, f"cutout{ztftype}": 1},
                    },
                    "kwargs": {
                        "limit": 1,
                    },
                }

                response = kowalski.query(query=query)
                if response.get("status", "error") == "success":
                    cutout = response.get("data", list(dict()))[0]
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


class AlertAuxHandler(BaseHandler):
    @auth_or_token
    def get(self, object_id: str = None):
        """
        ---
        single:
          description: Retrieve aux data for an objectId from Kowalski
          tags:
            - alerts
            - kowalski
          parameters:
            - in: path
              name: object_id
              required: true
              schema:
                type: string
            - in: query
              name: instrument
              required: false
              schema:
                type: str
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
              description: retrieved aux data
              content:
                application/json:
                  schema:
                    allOf:
                      - $ref: '#/components/schemas/Success'
                      - type: object
                        properties:
                          data:
                            type: object
            400:
              content:
                application/json:
                  schema: Error
        """
        instrument = self.get_query_argument("instrument", "ZTF").upper()
        if instrument not in INSTRUMENTS:
            raise ValueError("Instrument name not recognised")

        # allow access to public data only by default
        selector = {1}
        with self.Session():
            for stream in self.associated_user_object.streams:
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
                        {"$match": {"_id": object_id}},
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

            response = kowalski.query(query=query)

            if response.get("status", "error") == "success":
                alert_data = response.get("data")
                if len(alert_data) > 0:
                    alert_data = alert_data[0]
                else:
                    # len = 0 means that objectId does not exists on Kowalski
                    self.set_status(404)
                    self.finish()
                    return
            else:
                return self.error(response.get("message"))

            # grab and append most recent candid as it should not be in prv_candidates
            query = {
                "query_type": "aggregate",
                "query": {
                    "catalog": "ZTF_alerts",
                    "pipeline": [
                        {
                            "$match": {
                                "objectId": object_id,
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

            response = kowalski.query(query=query)

            if response.get("status", "error") == "success":
                latest_alert_data = response.get("data", list(dict()))
                if len(latest_alert_data) > 0:
                    latest_alert_data = latest_alert_data[0]
                else:
                    # len = 0 means that user has insufficient permissions to see objectId
                    self.set_status(404)
                    self.finish()
                    return
            else:
                return self.error(response.get("message"))

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
                        "radec": {object_id: [ra, dec]},
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

            response = kowalski.query(query=query)

            if response.get("status", "error") == "success":
                tns_data = response.get("data").get("TNS").get(object_id)
                alert_data["cross_matches"]["TNS"] = tns_data

            if not include_prv_candidates:
                alert_data.pop("prv_candidates", None)

            return self.success(data=alert_data)

        except Exception:
            _err = traceback.format_exc()
            return self.error(_err)


class AlertCutoutHandler(BaseHandler):
    @auth_or_token
    async def get(self, object_id: str = None):
        """
        ---
        summary: Serve alert cutout as fits or png
        tags:
          - alerts
          - kowalski

        parameters:
          - in: query
            name: instrument
            required: false
            schema:
              type: str
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
            default: png
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
        instrument = self.get_query_argument("instrument", "ZTF").upper()
        if instrument not in INSTRUMENTS:
            raise ValueError("Instrument name not recognised")

        # allow access to public data only by default
        selector = {1}
        with self.Session():
            for stream in self.associated_user_object.streams:
                if "ztf" in stream.name.lower():
                    selector.update(set(stream.altdata.get("selector", [])))

        selector = list(selector)

        try:
            candid = int(self.get_argument("candid"))
            cutout = self.get_argument("cutout").capitalize()
            file_format = self.get_argument("file_format", "png").lower()
            interval = self.get_argument("interval", default=None)
            stretch = self.get_argument("stretch", default=None)
            cmap = self.get_argument("cmap", default=None)

            known_cutouts = ["Science", "Template", "Difference"]
            if cutout not in known_cutouts:
                return self.error(
                    f"Cutout {cutout} of {object_id}/{candid} not in {str(known_cutouts)}"
                )
            known_file_formats = ["fits", "png"]
            if file_format not in known_file_formats:
                return self.error(
                    f"File format {file_format} of {object_id}/{candid}/{cutout} not in {str(known_file_formats)}"
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

            response = kowalski.query(query=query)

            if response.get("status", "error") == "success":
                alert = response.get("data", [dict()])[0]
            else:
                return self.error("No cutout found.")

            cutout_data = bj.loads(bj.dumps([alert[f"cutout{cutout}"]["stampData"]]))[0]

            # unzipped fits name
            fits_name = pathlib.Path(alert[f"cutout{cutout}"]["fileName"]).with_suffix(
                ""
            )

            # unzip and flip about y axis on the server side
            with gzip.open(io.BytesIO(cutout_data), "rb") as f:
                with fits.open(io.BytesIO(f.read()), ignore_missing_simple=True) as hdu:
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
