import datetime
import os
import subprocess
import base64
from pathlib import Path
import pandas as pd
import signal
import requests

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import init_db, Base, DBSession, Source, User
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
            ],
            super_admin_user.id,
            "load_demo_data token",
        )

    def assert_post(endpoint, post_data):
        r_status, r_data = api("POST", endpoint, post_data, token)
        if not (r_status == 200 and r_data["status"] == "success"):
            print("post_data:", post_data)
            raise RuntimeError(
                f'API call to {endpoint} failed with status {r_status}: {r_data}'
            )
        return r_data

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

            with status("Creating dummy groups & adding users"):
                data = assert_post(
                    "groups",
                    post_data={
                        "name": "Program B",
                        "group_admins": [
                            super_admin_user.username,
                        ],
                    },
                )
                data = assert_post(
                    "groups",
                    post_data={
                        "name": "Program A",
                        "group_admins": [
                            super_admin_user.username,
                            group_admin_user.username,
                        ],
                    },
                )
                group_id = data["data"]["id"]

                for u in [view_only_user, full_user]:
                    data = assert_post(
                        f"groups/{group_id}/users/{u.username}", post_data={"admin": False}
                    )

            with status("Creating dummy instruments"):
                data = assert_post(
                    "telescope",
                    post_data={
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
                    post_data={
                        "name": "P60 Camera",
                        "type": "phot",
                        "band": "optical",
                        "telescope_id": telescope1_id,
                    },
                )
                instrument1_id = data["data"]["id"]

                data = assert_post(
                    "telescope",
                    post_data={
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
                    post_data={
                        "name": "ALFOSC",
                        "type": "both",
                        "band": "optical",
                        "telescope_id": telescope2_id,
                    },
                )

            with status("Creating dummy sources & candidates"):
                SOURCES = [
                    {
                        "id": "14gqr",
                        "ra": 353.36647,
                        "dec": 33.646149,
                        "redshift": 0.063,
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
                        "group_ids": [group_id],
                        "comments": ["Frogs in the pond", "The eagle has landed"],
                    },
                ]

                (basedir / "static/thumbnails").mkdir(parents=True, exist_ok=True)
                for source_info in SOURCES:
                    comments = source_info.pop("comments")

                    data = assert_post("sources", post_data=source_info)
                    assert data["data"]["id"] == source_info["id"]

                    # Add one unsaved and one saved candidate per source
                    data = assert_post("candidates",
                                       post_data={**source_info, **{"id": source_info["id"] + "_2"}})
                    assert data["data"]["id"] == source_info["id"] + "_2"

                    # Saved candidates have associated source ID and saved by user ID
                    source_info["saved_as_source_by_id"] = super_admin_user.id
                    data = assert_post("candidates", post_data=source_info)
                    assert data["data"]["id"] == source_info["id"]

                    for comment in comments:
                        data = assert_post(
                            "comment",
                            post_data={"source_id": source_info["id"],
                                       "candidate_id": source_info["id"], "text": comment},
                        )
                        data = assert_post(
                            "comment",
                            post_data={"candidate_id": source_info["id"] + "_2", "text": comment},
                        )

                    phot_file = basedir / "skyportal/tests/data/phot.csv"
                    phot_data = pd.read_csv(phot_file)

                    data = assert_post(
                        "photometry",
                        post_data={
                            "source_id": source_info["id"],
                            "time_format": "iso",
                            "time_scale": "utc",
                            "instrument_id": instrument1_id,
                            "observed_at": phot_data.observed_at.tolist(),
                            "mag": phot_data.mag.tolist(),
                            "e_mag": phot_data.e_mag.tolist(),
                            "lim_mag": phot_data.lim_mag.tolist(),
                            "filter": phot_data["filter"].tolist(),
                        },
                    )
                    data = assert_post(
                        "photometry",
                        post_data={
                            "source_id": source_info["id"] + "_2",
                            "time_format": "iso",
                            "time_scale": "utc",
                            "instrument_id": instrument1_id,
                            "observed_at": phot_data.observed_at.tolist(),
                            "mag": phot_data.mag.tolist(),
                            "e_mag": phot_data.e_mag.tolist(),
                            "lim_mag": phot_data.lim_mag.tolist(),
                            "filter": phot_data["filter"].tolist(),
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
                            post_data={
                                "source_id": source_info["id"],
                                "observed_at": str(datetime.datetime(2014, 10, 24)),
                                "instrument_id": 1,
                                "wavelengths": df.wavelength.tolist(),
                                "fluxes": df.flux.tolist(),
                            },
                        )
                        data = assert_post(
                            "spectrum",
                            post_data={
                                "source_id": source_info["id"] + "_2",
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
                            post_data={
                                "source_id": source_info["id"],
                                "data": thumbnail_data,
                                "ttype": ttype,
                            },
                        )
                        data = assert_post(
                            "thumbnail",
                            post_data={
                                "source_id": source_info["id"] + "_2",
                                "data": thumbnail_data,
                                "ttype": ttype,
                            },
                        )

                    source = Source.query.get(source_info["id"])
                    source.add_linked_thumbnails()
                    cand = Source.query.get(source_info["id"] + "_2")
                    cand.add_linked_thumbnails()
        finally:
            if not app_already_running:
                print("Terminating web app")
                os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
