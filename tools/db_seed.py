import os
import subprocess
from pathlib import Path
import signal
import requests

import tdtax
from social_tornado.models import TornadoStorage

from baselayer.app.env import load_env
from baselayer.app.model_util import status
from skyportal.models import init_db, DBSession, User
from skyportal.model_util import create_token
from skyportal.tests import api
from baselayer.tools.test_frontend import verify_server_availability


if __name__ == "__main__":
    """Insert test data"""
    env, cfg = load_env()
    basedir = Path(os.path.dirname(__file__)) / ".."

    with status(f"Connecting to database {cfg['database']['database']}"):
        init_db(**cfg["database"])

    with status(f"Creating users"):

        users = []
        for u in cfg['db_seed'].get('users', []):
            users.append(
                User(username=u["username"], role_ids=u["role_ids"])
            )

        DBSession().add_all(users)

        for u in users:
            DBSession().add(
                TornadoStorage.user.create_social_auth(u, u.username, "google-oauth2")
            )

    with status("Creating tokens"):

        tokens = {}
        for u in users:
            for t in u.get("tokens", []):
                tokens[t["name"]] = create_token(
                    t["permissions"],
                    u.id,
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
            response_status, data = api("GET", "sysinfo", token=tokens[0])
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

            with status("Creating groups"):
                group_ids = []
                group_dict = {}
                for g in cfg['db_seed'].get('groups', []):
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

            with status("Creating Taxonomies"):

                for tax in cfg['db_seed'].get('taxonomies', []):
                    name = tax["name"]
                    provenance = tax.get("provenance")

                    if tax["tdtax"]:
                        hierarchy = tdtax.taxonomy
                        version = tdtax.__version__
                    else:
                        hierarchy = tax["hierarchy"]
                        version = tax["version"]

                    group_ids = [group_dict[g] for g in tax["groups"]]
                    data = assert_post(
                        "taxonomy",
                        {
                            "name": name,
                            "hierarchy": hierarchy,
                            "group_ids": group_ids,
                            "provenance": provenance,
                            "version": version,
                        },
                        tokens[tax["token"]]

                    )
                    taxonomy_id = data["data"]["id"]
                    print(name, taxonomy_id)
            with status("Creating telescopes & instruments"):
                # TBD
                pass

        finally:
            if not app_already_running:
                print("Terminating web app")
                os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
