import os
import sys
import base64
from pathlib import Path
import textwrap

import pandas as pd
import yaml
from yaml import Loader
import tdtax

from baselayer.app.env import load_env, parser
from baselayer.app.model_util import status
from skyportal.tests import api


if __name__ == "__main__":
    parser.description = 'Load data into SkyPortal'
    parser.add_argument('data_files', type=str, nargs='+',
                        help='YAML files with data to load')
    parser.add_argument('--host',
                        help=textwrap.dedent('''Fully specified URI of the running SkyPortal instance.
                             E.g., https://myserver.com:9000.

                             Defaults to http://localhost on the port specified
                             in the SkyPortal configuration file.'''))
    parser.add_argument('--token',
                        help=textwrap.dedent('''Token required for accessing the SkyPortal API.

                             By default, SkyPortal produces a token that is
                             written to .tokens.yaml.  If no token is specified
                             here, that token will be used.'''))

    env, cfg = load_env()

    ## TODO: load multiple files
    fname = env.data_files[0]
    src = yaml.load(open(fname, "r"), Loader=Loader)

    def get_token():
        if env.token:
            return env.token

        try:
            token = yaml.load(open('.tokens.yaml'), Loader=yaml.Loader)['INITIAL_ADMIN']
            return token
        except:
            print('Error: no token specified, and no suitable token found in .tokens.yaml')
            sys.exit(-1)

    admin_token = get_token()

    def assert_post(endpoint, data, token=admin_token):
        response_status, data = api("POST", endpoint,
                                    data=data,
                                    token=token,
                                    host=env.host)
        if not response_status == 200 and data["status"] == "success":
            raise RuntimeError(
                f'API call to {endpoint} failed with status {status}: {data["message"]}'
            )
        return data

    # if src.get("users") is not None:
    #     with status(f"Creating users"):

    #         users = []
    #         for user in src.get('users', []):
    #             users.append(
    #                 User(username=user["username"], role_ids=user["role_ids"])
    #             )
    #         DBSession().add_all(users)
    #         for user in users:
    #             DBSession().add(
    #                 TornadoStorage.user.create_social_auth(user, user.username, "google-oauth2")
    #             )
    #         users_dict = {user.username: user.id for user in users}

    #     with status("Creating tokens"):

    #         tokens = {}
    #         for user in src.get('users', []):
    #             for t in user.get("tokens", []):
    #                 tokens[t["name"]] = create_token(
    #                     t["permissions"],
    #                     users_dict[user["username"]],
    #                     t["name"]
    #                 )
    #                 if t.get("print", False):
    #                     print(t["name"], tokens[t["name"]])

# TODO: Use API directly to verify server availability
#    verify_server_availability(server_url)

    if src.get("groups") is not None:
        with status("Creating groups"):
            group_ids = []
            group_dict = {}
            filter_dict = {}
            for group in src.get('groups', []):
                data = assert_post(
                    "groups",
                    {
                        "name": group["name"],
                        "group_admins": group["group_admins"]
                    }
                )
                group_ids.append(data["data"]["id"])
                group_dict[group["name"]] = group_ids[-1]

                for filt in group.get("filters", []):
                    data = assert_post(
                        "filters",
                        {
                            "group_id": group_ids[-1],
                            "query_string": filt["query_string"]
                        }
                    )
                    filter_dict[filt["name"]] = data["data"]["id"]

                for member in group.get("members", []):
                    data = assert_post(
                        f"groups/{group_ids[-1]}/users/{member['username']}",
                        {"admin": member.get('admin', False)}
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
                    payload
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

            for telescope in tel_src:
                if telescope.get("group_names") is None:
                    group_ids = tel_group_ids
                else:
                    group_ids = [group_dict[g] for g in telescope["group_names"]]
                if telescope.get("nickname") is not None:
                    nickname = telescope["nickname"]
                else:
                    nickname = telescope["id"]
                if telescope.get("token") is not None:
                    token_name = telescope["token"]
                else:
                    token_name = tel_token

                data = assert_post(
                    "telescope",
                    data={
                        "name": telescope["name"],
                        "nickname": nickname,
                        "lat": telescope.get("lat", 0.0),
                        "lon": telescope.get("lon", 0.0),
                        "elevation": telescope.get("elevation", 0.0),
                        "diameter": telescope.get("diameter", 1.0),
                        "group_ids": group_ids
                    }
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

                for instrument in ins_src:
                    if instrument.get("token") is not None:
                        token_name = instrument["token"]
                    else:
                        token_name = ins_token

                    if instrument.get("telescope_nickname") is not None:
                        telname = instrument["telescope_nickname"]
                    else:
                        telname = instrument.get("telescope_id")
                    telid = telescope_dict[telname]

                    data = assert_post(
                        "instrument",
                        data={
                            "name": instrument["name"],
                            "type": instrument["type"],
                            "band": instrument["band"],
                            "telescope_id": telid,
                            "filters": instrument.get("filters", [])
                        }
                    )
                    instrument_dict[instrument["name"]] = data["data"]["id"]
    if src.get("sources") is not None:
        with status("Loading Source and Candidates"):
            Path("static/thumbnails").mkdir(parents=True, exist_ok=True)
            for source in src.get("sources"):
                sinfo = [{"id": source["id"], "ra": source["ra"],
                          "dec": source["dec"], "save_source": True,
                          "redshift": source.get("redshift", 0.0),
                          "altdata": source.get("altdata", None),
                          "cand_filts": source["candidate"]["candidate_filters"],
                          "comments": source.get("comments", [])}]
                if source.get("unsaved_candidate_copy") is not None:
                    sinfo.append(
                        {"id": source["unsaved_candidate_copy"]["candidate_id"],
                         "ra": source["ra"],
                         "dec": source["dec"], "save_source": False,
                         "redshift": source.get("redshift", 0.0),
                         "altdata": source.get("altdata", None),
                         "cand_filts": source["unsaved_candidate_copy"]["candidate_filters"],
                         "comments": source["unsaved_candidate_copy"].get("comments", [])}
                    )
                group_ids = [group_dict[g] for g in source["group_names"]]

                if source.get("photometry") is not None:
                    phot_file = source["photometry"]["data"]
                    phot_data = pd.read_csv(phot_file)
                    phot_instrument_name = source["photometry"]["instrument_name"]

                if source.get("spectroscopy") is not None:
                    spec_file = source["spectroscopy"]["data"]
                    spec_data = pd.read_csv(spec_file)
                    spec_instrument_name = source["spectroscopy"]["instrument_name"]
                    observed_at = source["spectroscopy"]["observed_at"]
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
                            }
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
                        }
                    )

                    for comment in si["comments"]:
                        data = assert_post(
                            "comment",
                            data={"obj_id": si["id"], "text": comment}
                        )

                    if source.get("photometry") is not None:
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
                            }
                        )

                    if source.get("spectroscopy") is not None:
                        for i, df in spec_data.groupby("instrument_id"):
                            # TODO: spec.csv shouldn't hard code the
                            # instrument ID. For now, use what'source
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
                                }
                            )

                    if source.get("thumbnails") is not None:
                        for ttype, fname in source.get("thumbnails").items():
                            thumbnail_data = base64.b64encode(
                                open(os.path.abspath(fname), "rb").read()
                            )
                            data = assert_post(
                                "thumbnail",
                                data={
                                    "obj_id": si["id"],
                                    "data": thumbnail_data,
                                    "ttype": ttype,
                                }
                            )

                        #Obj.query.get(si["id"]).add_linked_thumbnails()
