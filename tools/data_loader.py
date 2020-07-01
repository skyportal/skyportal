import os
import sys
import subprocess
from pathlib import Path
from pathlib import PurePosixPath
import signal
import requests

import yaml
import tdtax
from social_tornado.models import TornadoStorage

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from skyportal.models import Base, init_db, DBSession, User
from skyportal.model_util import setup_permissions, create_token
from skyportal.tests import api
from baselayer.tools.test_frontend import verify_server_availability


if __name__ == "__main__":
    """Insert test data"""
    env, cfg = load_env()
    basedir = Path(os.path.dirname(__file__)) / ".."
    topdir = PurePosixPath(os.path.abspath(__file__)).parent.parent

    data_source = sys.argv[1]  # get the data source name from the command-line
    if cfg['data_load'].get(data_source) is None:
        raise RuntimeError(
            f'Make sure that {data_source} is in the data_load section of '
            'your config.yaml.'
        )

    if cfg['data_load'][data_source].get("file") is not None:
        fname = str(topdir / cfg['data_load'][data_source]["file"])
        print(fname)
        src = yaml.load(open(fname, "r"))
    else:
        src =cfg['data_load'][data_source]

    with status(f"Connecting to database {cfg['database']['database']}"):
        init_db(**cfg["database"])

    if src.get("drop_tables", False):
        with status("Dropping all tables"):
            drop_tables()

    if src.get("create_tables", False):
        with status("Creating tables"):
            create_tables()

    if src.get("print_tables", False):
        for model in Base.metadata.tables:
            print("    -", model)

    if src.get("create_permissions", False):
        with status(f"Creating permissions"):
            setup_permissions()

    if src.get("users") is not None:
        with status(f"Creating users"):

            users = []
            for u in src.get('users', []):
                users.append(
                    User(username=u["username"], role_ids=u["role_ids"])
                )
            DBSession().add_all(users)
            for u in users:
                DBSession().add(
                    TornadoStorage.user.create_social_auth(u, u.username, "google-oauth2")
                )
            users_dict = {u.username: u.id for u in users}

        with status("Creating tokens"):

            tokens = {}
            for u in src.get('users', []):
                for t in u.get("tokens", []):
                    tokens[t["name"]] = create_token(
                        t["permissions"],
                        users_dict[u["username"]],
                        t["name"]
                    )

    def assert_post(endpoint, data, token):
        response_status, data = api("POST", endpoint, data, token)
        if not response_status == 200 and data["status"] == "success":
            raise RuntimeError(
                f'API call to {endpoint} failed with status {status}: {data["message"]}'
            )
        return data

    with status("Launching web app & executing API calls"):
        try:
            response_status, data = api("GET", "sysinfo", token=list(tokens.values())[0])
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

            if src.get("groups") is not None:
                with status("Creating groups"):
                    group_ids = []
                    group_dict = {}
                    for g in src.get('groups', []):
                        data = assert_post(
                            "groups",
                            {
                                "name": g["name"],
                                "group_admins": g["group_admins"]
                            },
                            tokens[g["token"]]
                        )
                        group_ids.append(data["data"]["id"])
                        group_dict[g["name"]] = group_ids[-1]

            if src.get("taxonomies") is not None:
                with status("Creating Taxonomies"):

                    for tax in src.get('taxonomies', []):
                        name = tax["name"]
                        provenance = tax.get("provenance")

                        if tax["tdtax"]:
                            hierarchy = tdtax.taxonomy
                            version = tdtax.__version__
                        else:
                            hierarchy = tax["hierarchy"]
                            tdtax.validate(hierarchy, tdtax.schema)
                            version = tax["version"]

                        group_ids = [group_dict[g] for g in tax["groups"]]
                        payload = {
                                "name": name,
                                "hierarchy": hierarchy,
                                "group_ids": group_ids,
                                "provenance": provenance,
                                "version": version,
                        }
                        data = assert_post(
                            "taxonomy",
                            payload,
                            tokens[tax["token"]]

                        )
            if src.get("telescopes") is not None:
                with status("Creating telescopes"):
                    telescope_dict = {}
                    for t in src.get("telescopes"):
                        group_ids = [group_dict[g] for g in t["group_names"]]
                        data = assert_post(
                                "telescope",
                                data={
                                    "name": t["name"],
                                    "nickname": t["nickname"],
                                    "lat": t["lat"],
                                    "lon": t["lon"],
                                    "elevation": t.get("elevation", 0.0),
                                    "diameter": t.get("elevation", 1.0),
                                    "group_ids": group_ids
                                },
                                token=tokens[t["token"]]
                        )
                        telescope_dict[t["nickname"]] = data["data"]["id"]
                if src.get("instruments") is not None:
                    with status("Creating instruments"):
                        instrument_dict = {}
                        for i in src.get("instruments"):
                            telid = telescope_dict[i["telescope_nickname"]]
                            data = assert_post(
                                "instrument",
                                data={
                                    "name": i["name"],
                                    "type": i["type"],
                                    "band": i["band"],
                                    "telescope_id": telid,
                                    "filters": i.get("filters", [])
                                },
                                token=tokens[i["token"]]
                            )
                            instrument_dict[i["name"]] = data["data"]["id"]
            if src.get("sources") is not None:
                with status("Loading Source and Candidates"):
                    (basedir / "static/thumbnails").mkdir(parents=True, exist_ok=True)
                    for s in src.get("sources"):
                        group_ids = [group_dict[g] for g in s["group_names"]]
                        data = assert_post(
                            "sources",
                            data={
                                  "id": s["id"],
                                  "ra": s["ra"],
                                  "dec": s["dec"],
                                  "redshift": s.get("redshift", 0.0),
                                  "altdata": s.get("altdata", None),
                                  "group_ids": group_ids
                                  },
                            token=tokens[s["token"]]
                        )
                        data = assert_post(
                            "candidates",
                            data={
                                  "id": s["id"],
                                  "ra": s["ra"],
                                  "dec": s["dec"],
                                  "redshift": s.get("redshift", 0.0),
                                  "altdata": s.get("altdata", None),

                                  },
                            token=tokens[s["token"]]


        finally:
            if not app_already_running:
                print("Terminating web app")
                os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
