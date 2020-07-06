import os
import sys
import subprocess
import base64
from pathlib import Path
from pathlib import PurePosixPath
import signal
import requests

import pandas as pd
import yaml
from yaml import Loader
import tdtax
from social_tornado.models import TornadoStorage

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from skyportal.models import Base, init_db, Obj, DBSession, User
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
        src = yaml.load(open(fname, "r"), Loader=Loader)
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
                    if t.get("print", False):
                        print(t["name"], tokens[t["name"]])

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
                    filter_dict = {}
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

                        for f in g.get("filters", []):
                            data = assert_post(
                                "filters",
                                {
                                    "group_id": group_ids[-1],
                                    "query_string": f["query_string"]
                                },
                                tokens[g["token"]]
                            )
                            filter_dict[f["name"]] = data["data"]["id"]

                        for m in g.get("members", []):
                            data = assert_post(
                                f"groups/{group_ids[-1]}/users/{m['username']}",
                                {"admin": m.get('admin', False)},
                                tokens[g["token"]]
                            )
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
                with status("Creating Telescopes"):
                    telescope_dict = {}
                    tel_src = src.get("telescopes")
                    if isinstance(tel_src, dict) and \
                            src["telescopes"].get("file") is not None:
                        # we're asked to load a file containing telescopes
                        fname = str(topdir / src["telescopes"]["file"])
                        tel_src = yaml.load(open(fname, "r"), Loader=Loader)
                        tel_group_ids = [group_dict[g] for g in
                                         src["telescopes"]["group_names"]]
                        tel_token = src["telescopes"]["token"]

                    for t in tel_src:
                        if t.get("group_names") is None:
                            group_ids = tel_group_ids
                        else:
                            group_ids = [group_dict[g] for g in t["group_names"]]
                        if t.get("nickname") is not None:
                            nickname = t["nickname"]
                        else:
                            nickname = t["id"]
                        if t.get("token") is not None:
                            token_name = t["token"]
                        else:
                            token_name = tel_token

                        data = assert_post(
                            "telescope",
                            data={
                                "name": t["name"],
                                "nickname": nickname,
                                "lat": t.get("lat", 0.0),
                                "lon": t.get("lon", 0.0),
                                "elevation": t.get("elevation", 0.0),
                                "diameter": t.get("diameter", 1.0),
                                "group_ids": group_ids
                            },
                            token=tokens[token_name]
                        )
                        telescope_dict[nickname] = data["data"]["id"]
                if src.get("instruments") is not None:
                    with status("Creating instruments"):
                        instrument_dict = {}
                        ins_src = src.get("instruments")
                        if isinstance(ins_src, dict) and \
                                src["instruments"].get("file") is not None:
                            # we're asked to load a file containing telescopes
                            fname = str(topdir / src["instruments"]["file"])
                            ins_src = yaml.load(open(fname, "r"), Loader=Loader)
                            ins_token = src["instruments"]["token"]

                        for i in ins_src:
                            if i.get("token") is not None:
                                token_name = i["token"]
                            else:
                                token_name = ins_token

                            if i.get("telescope_nickname") is not None:
                                telname = i["telescope_nickname"]
                            else:
                                telname = i.get("telescope_id")
                            telid = telescope_dict[telname]
                            # print(telid, telname, token_name, tokens[token_name], group_ids)
                            data = assert_post(
                                "instrument",
                                data={
                                    "name": i["name"],
                                    "type": i["type"],
                                    "band": i["band"],
                                    "telescope_id": telid,
                                    "filters": i.get("filters", [])
                                },
                                token=tokens[token_name]
                            )
                            instrument_dict[i["name"]] = data["data"]["id"]
            if src.get("sources") is not None:
                with status("Loading Source and Candidates"):
                    (basedir / "static/thumbnails").mkdir(parents=True, exist_ok=True)
                    for s in src.get("sources"):
                        sinfo = [{"id": s["id"], "ra": s["ra"],
                                  "dec": s["dec"], "save_source": True,
                                  "redshift": s.get("redshift", 0.0),
                                  "altdata": s.get("altdata", None),
                                  "cand_filts": s["candidate"]["candidate_filters"],
                                  "comments": s.get("comments", [])}]
                        if s.get("unsaved_candidate_copy") is not None:
                            sinfo.append(
                                {"id": s["unsaved_candidate_copy"]["candidate_id"],
                                 "ra": s["ra"],
                                 "dec": s["dec"], "save_source": False,
                                 "redshift": s.get("redshift", 0.0),
                                 "altdata": s.get("altdata", None),
                                 "cand_filts": s["unsaved_candidate_copy"]["candidate_filters"],
                                 "comments": s["unsaved_candidate_copy"].get("comments", [])}
                            )
                        group_ids = [group_dict[g] for g in s["group_names"]]

                        if s.get("photometry") is not None:
                            phot_file = basedir / s["photometry"]["data"]
                            phot_data = pd.read_csv(phot_file)
                            phot_instrument_name = s["photometry"]["instrument_name"]

                        if s.get("spectroscopy") is not None:
                            spec_file = basedir / s["spectroscopy"]["data"]
                            spec_data = pd.read_csv(spec_file)
                            spec_instrument_name = s["spectroscopy"]["instrument_name"]
                            observed_at = s["spectroscopy"]["observed_at"]
                        for si in sinfo:
                            if si["save_source"]:
                                data = assert_post(
                                    "sources",
                                    data={
                                        "id": si["id"],
                                        "ra": si["ra"],
                                        "dec": si["dec"],
                                        "redshift": si["redshift"],
                                        "altdata": si["altdata"],
                                        "group_ids": group_ids
                                    },
                                    token=tokens[s["token"]]
                                )
                            filter_ids = [filter_dict[f] for f in si["cand_filts"]]
                            data = assert_post(
                                "candidates",
                                data={
                                    "id": si["id"],
                                    "ra": si["ra"],
                                    "dec": si["dec"],
                                    "redshift": si["redshift"],
                                    "altdata": si["altdata"],
                                    "filter_ids": filter_ids
                                },
                                token=tokens[s["token"]]
                            )

                            for comment in si["comments"]:
                                data = assert_post(
                                    "comment",
                                    data={"obj_id": si["id"], "text": comment},
                                    token=tokens[s["token"]]
                                )

                            if s.get("photometry") is not None:
                                data = assert_post(
                                    "photometry",
                                    data={
                                        "obj_id": si['id'],
                                        "instrument_id":
                                            instrument_dict[phot_instrument_name],
                                        "mjd": phot_data.mjd.tolist(),
                                        "flux": phot_data.flux.tolist(),
                                        "fluxerr": phot_data.fluxerr.tolist(),
                                        "zp": phot_data.zp.tolist(),
                                        "magsys": phot_data.magsys.tolist(),
                                        "filter": phot_data["filter"].tolist(),
                                        "group_ids": group_ids,
                                    },
                                    token=tokens[s["token"]]
                                )

                            if s.get("spectroscopy") is not None:
                                for i, df in spec_data.groupby("instrument_id"):
                                    # TODO: spec.csv shouldn't hard code the
                                    # instrument ID. For now, use what's
                                    # in the config for instrument
                                    data = assert_post(
                                        "spectrum",
                                        data={
                                            "obj_id": si["id"],
                                            "observed_at": observed_at,
                                            "instrument_id":
                                                instrument_dict[spec_instrument_name],
                                            "wavelengths": df.wavelength.tolist(),
                                            "fluxes": df.flux.tolist(),
                                        },
                                        token=tokens[s["token"]]
                                    )

                            if s.get("thumbnails") is not None:
                                for ttype, fname in s.get("thumbnails").items():
                                    fpath = basedir / f"{fname}"
                                    thumbnail_data = base64.b64encode(
                                        open(os.path.abspath(fpath), "rb").read()
                                    )
                                    data = assert_post(
                                        "thumbnail",
                                        data={
                                            "obj_id": si["id"],
                                            "data": thumbnail_data,
                                            "ttype": ttype,
                                        },
                                        token=tokens[s["token"]]
                                    )

                                Obj.query.get(si["id"]).add_linked_thumbnails()

        finally:
            if not app_already_running:
                print("Terminating web app")
                os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
