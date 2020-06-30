import datetime
import os
import subprocess
import base64
from pathlib import Path
import shutil
import pandas as pd
import signal
import requests

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import init_db, Base, DBSession, Obj, User
from skyportal.model_util import setup_permissions, create_token
from skyportal.tests import api
from baselayer.tools.test_frontend import verify_server_availability


if __name__ == "__main__":
    """Insert test data"""
    env, cfg = load_env()
    basedir = Path(os.path.dirname(__file__)) / ".."

    with status(f"Connecting to database {cfg['database']['database']}"):
        init_db(**cfg["database"])

    with status("Dropping all tables"):
        drop_tables()

    with status("Creating tables"):
        create_tables()

    for model in Base.metadata.tables:
        print("    -", model)

    with status(f"Creating permissions"):
        setup_permissions()

    with status(f"Creating dummy users"):
        super_admin_user = User(
            username="testuser@cesium-ml.org", role_ids=["Super admin"]
        )
        group_admin_user = User(
            username="groupadmin@cesium-ml.org", role_ids=["Super admin"]
        )
        full_user = User(username="fulluser@cesium-ml.org", role_ids=["Full user"])
        view_only_user = User(
            username="viewonlyuser@cesium-ml.org", role_ids=["View only"]
        )
        DBSession().add_all(
            [super_admin_user, group_admin_user, full_user, view_only_user]
        )

        for u in [super_admin_user, group_admin_user, full_user, view_only_user]:
            DBSession().add(
                TornadoStorage.user.create_social_auth(u, u.username, "google-oauth2")
            )

    with status("Creating token"):
        token = create_token(
            [
                "Manage groups",
                "Manage sources",
                "Upload data",
                "Comment",
                "Manage users",
                "System admin",
            ],
            super_admin_user.id,
            "load_demo_data token",
        )

    def assert_post(endpoint, data):
        response_status, data = api("POST", endpoint, data, token)
        if not response_status == 200 and data["status"] == "success":
            raise RuntimeError(
                f'API call to {endpoint} failed with status {status}: {data["message"]}'
            )
        return data

    with status("Launching web app & executing API calls"):
        try:
            response_status, data = api("GET", "sysinfo", token=token)
            app_already_running = True
        except requests.ConnectionError:
            app_already_running = False
            web_client = subprocess.Popen(
                ["make", "run"], cwd=basedir, preexec_fn=os.setsid
            )

        server_url = f"http://localhost:{cfg['ports.app']}"
        print()
        print(f"Waiting for server to appear at {server_url}...")

        try:
            verify_server_availability(server_url)
            print("App running - continuing with API calls")

            with status("Creating dummy groups & filter & adding users"):
                data = assert_post(
                    "groups",
                    data={
                        "name": "Program A",
                        "group_admins": [
                            super_admin_user.username,
                            group_admin_user.username,
                        ],
                    },
                )
                group_id = data["data"]["id"]

                data = assert_post(
                    "groups",
                    data={
                        "name": "Program B",
                        "group_admins": [
                            super_admin_user.username,
                        ],
                    },
                )

                data = assert_post(
                    "filters",
                    data={
                        "group_id": group_id,
                        "query_string": "sample_query_string",
                    },
                )
                filter_id = data["data"]["id"]

                for u in [view_only_user, full_user]:
                    data = assert_post(
                        f"groups/{group_id}/users/{u.username}", data={"admin": False}
                    )

            with status("Creating dummy telescopes & instruments"):
                data = assert_post(
                    "telescope",
                    data={
                        "name": "Palomar 1.5m",
                        "nickname": "P60",
                        "lat": 33.3633675,
                        "lon": -116.8361345,
                        "elevation": 1870,
                        "diameter": 1.5,
                        "group_ids": [group_id],
                    },
                )
                telescope1_id = data["data"]["id"]

                data = assert_post(
                    "instrument",
                    data={
                        "name": "P60 Camera",
                        "type": "phot",
                        "band": "V",
                        "telescope_id": telescope1_id,
                        "filters": ["ztfg", "ztfr", "ztfi"]
                    },
                )
                instrument1_id = data["data"]["id"]

                data = assert_post(
                    "telescope",
                    data={
                        "name": "Nordic Optical Telescope",
                        "nickname": "NOT",
                        "lat": 28.75,
                        "lon": 17.88,
                        "elevation": 1870,
                        "diameter": 2.56,
                        "group_ids": [group_id],
                    },
                )
                telescope2_id = data["data"]["id"]

                data = assert_post(
                    "instrument",
                    data={
                        "name": "ALFOSC",
                        "type": "both",
                        "band": "V",
                        "telescope_id": telescope2_id,
                    },
                )

            with status("Creating dummy candidates & sources"):
                SOURCES = [
                    {
                        "id": "14gqr",
                        "ra": 353.36647,
                        "dec": 33.646149,
                        "redshift": 0.063,
                        "altdata": {"simbad": {"class": "RRLyr"}},
                        "group_ids": [group_id],
                        "comments": [
                            "No source at transient location to R>26 in LRIS imaging",
                            "Strong calcium lines have emerged.",
                        ],
                    },
                    {
                        "id": "16fil",
                        "ra": 322.718872,
                        "dec": 27.574113,
                        "redshift": 0.0,
                        "altdata": {"simbad": {"class": "Mira"}},
                        "group_ids": [group_id],
                        "comments": ["Frogs in the pond", "The eagle has landed"],
                    },
                ]

                (basedir / "static/thumbnails").mkdir(parents=True, exist_ok=True)
                for source_info in SOURCES:
                    comments = source_info.pop("comments")

                    data = assert_post("sources", data=source_info)
                    assert data["data"]["id"] == source_info["id"]

                    _ = source_info.pop("group_ids")
                    data = assert_post("candidates", data={**source_info,
                                                           "filter_ids": [filter_id]})
                    assert data["data"]["id"] == source_info["id"]

                    # Add candidates with no associated sources
                    data = assert_post("candidates", data={**source_info,
                                                           "filter_ids": [filter_id],
                                                           "id": f"{source_info['id']}_unsaved_copy"})
                    assert data["data"]["id"] == f"{source_info['id']}_unsaved_copy"

                    for comment in comments:
                        data = assert_post(
                            "comment",
                            data={"obj_id": source_info["id"], "text": comment},
                        )
                        data = assert_post(
                            "comment",
                            data={"obj_id": f"{source_info['id']}_unsaved_copy", "text": comment},
                        )

                    phot_file = basedir / "skyportal/tests/data/phot.csv"
                    phot_data = pd.read_csv(phot_file)

                    data = assert_post(
                        "photometry",
                        data={
                            "obj_id": source_info['id'],
                            "instrument_id": instrument1_id,
                            "mjd": phot_data.mjd.tolist(),
                            "flux": phot_data.flux.tolist(),
                            "fluxerr": phot_data.fluxerr.tolist(),
                            "zp": phot_data.zp.tolist(),
                            "magsys": phot_data.magsys.tolist(),
                            "filter": phot_data["filter"].tolist(),
                            "group_ids": [group_id],
                        },
                    )
                    data = assert_post(
                        "photometry",
                        data={
                            "obj_id": f"{source_info['id']}_unsaved_copy",
                            "instrument_id": instrument1_id,
                            "mjd": phot_data.mjd.tolist(),
                            "flux": phot_data.flux.tolist(),
                            "fluxerr": phot_data.fluxerr.tolist(),
                            "zp": phot_data.zp.tolist(),
                            "magsys": phot_data.magsys.tolist(),
                            "filter": phot_data["filter"].tolist(),
                            "group_ids": [group_id],
                        },
                    )

                    spec_file = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        "skyportal",
                        "tests",
                        "data",
                        "spec.csv",
                    )
                    spec_data = pd.read_csv(spec_file)
                    for i, df in spec_data.groupby("instrument_id"):
                        data = assert_post(
                            "spectrum",
                            data={
                                "obj_id": source_info["id"],
                                "observed_at": str(datetime.datetime(2014, 10, 24)),
                                "instrument_id": 1,
                                "wavelengths": df.wavelength.tolist(),
                                "fluxes": df.flux.tolist(),
                            },
                        )
                        data = assert_post(
                            "spectrum",
                            data={
                                "obj_id": f"{source_info['id']}_unsaved_copy",
                                "observed_at": str(datetime.datetime(2014, 10, 24)),
                                "instrument_id": 1,
                                "wavelengths": df.wavelength.tolist(),
                                "fluxes": df.flux.tolist(),
                            },
                        )

                    for ttype in ["new", "ref", "sub"]:
                        fname = f'{source_info["id"]}_{ttype}.png'
                        fpath = basedir / f"skyportal/tests/data/{fname}"
                        thumbnail_data = base64.b64encode(
                            open(os.path.abspath(fpath), "rb").read()
                        )
                        data = assert_post(
                            "thumbnail",
                            data={
                                "obj_id": source_info["id"],
                                "data": thumbnail_data,
                                "ttype": ttype,
                            },
                        )
                        data = assert_post(
                            "thumbnail",
                            data={
                                "obj_id": f"{source_info['id']}_unsaved_copy",
                                "data": thumbnail_data,
                                "ttype": ttype,
                            },
                        )

                    Obj.query.get(source_info["id"]).add_linked_thumbnails()
                    Obj.query.get(f"{source_info['id']}_unsaved_copy").add_linked_thumbnails()
        finally:
            if not app_already_running:
                print("Terminating web app")
                os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
