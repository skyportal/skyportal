import json
import tempfile
import urllib

import requests
from utils.tns import get_IAUname

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from baselayer.log import make_log

from ....models import (
    Spectrum,
    SpectrumObserver,
    SpectrumReducer,
    TNSRobot,
)
from ...base import BaseHandler

_, cfg = load_env()

TNS_URL = cfg["app.tns.endpoint"]
upload_url = urllib.parse.urljoin(TNS_URL, "api/set/file-upload")
report_url = urllib.parse.urljoin(TNS_URL, "api/set/bulk-report")

log = make_log("api/spectrum_tns")


class SpectrumTNSHandler(BaseHandler):
    @auth_or_token
    def post(self, spectrum_id):
        """
        ---
        summary: Submit a (classification) spectrum to TNS
        description: Submit a (classification) spectrum to TNS
        tags:
          - tns
          - spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
          - in: query
            name: tnsrobotID
            schema:
              type: int
            required: true
            description: |
                SkyPortal TNS Robot ID
          - in: query
            name: classificationID
            schema:
              type: string
            description: |
                Classification ID (see TNS documentation at
                https://www.wis-tns.org/content/tns-getting-started
                for options)
          - in: query
            name: classifiers
            schema:
              type: string
            description: |
                List of those performing classification.
          - in: query
            name: spectrumType
            schema:
              type: string
            description: |
                Type of spectrum that this is. Valid options are:
                ['object', 'host', 'sky', 'arcs', 'synthetic']
          - in: query
            name: spectrumComment
            schema:
              type: string
            description: |
                Comment on the spectrum.
          - in: query
            name: classificationComment
            schema:
              type: string
            description: |
                Comment on the classification.
        responses:
          200:
            content:
              application/json:
                schema: SingleSpectrum
          400:
            content:
              application/json:
                schema: Error
        """

        # for now this is deprecated, as the feature is not used by any user
        # + needs to be updated to use the new TNS submission queue
        return self.error("This feature is deprecated")

        # data = self.get_json()
        # tnsrobotID = data.get("tnsrobotID")
        # classificationID = data.get("classificationID", None)
        # classifiers = data.get("classifiers", "")
        # spectrum_type = data.get("spectrumType", "")
        # spectrum_comment = data.get("spectrumComment", "")
        # classification_comment = data.get("classificationComment", "")
        #
        # if tnsrobotID is None:
        #     return self.error("tnsrobotID is required")
        #
        # with self.Session() as session:
        #     tnsrobot = session.scalars(
        #         TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
        #     ).first()
        #     if tnsrobot is None:
        #         return self.error(f"No TNSRobot available with ID {tnsrobotID}")
        #
        #     altdata = tnsrobot.altdata
        #     if not altdata:
        #         return self.error("Missing TNS information.")
        #
        #     spectrum = session.scalars(
        #         Spectrum.select(session.user_or_token).where(Spectrum.id == spectrum_id)
        #     ).first()
        #     if spectrum is None:
        #         return self.error(f"No spectrum with ID {spectrum_id}")
        #
        #     spec_dict = recursive_to_dict(spectrum)
        #     spec_dict["instrument_name"] = spectrum.instrument.name
        #     spec_dict["groups"] = spectrum.groups
        #     spec_dict["reducers"] = spectrum.reducers
        #     spec_dict["observers"] = spectrum.observers
        #     spec_dict["owner"] = spectrum.owner
        #
        #     external_reducer = session.scalars(
        #         SpectrumReducer.select(session.user_or_token).where(
        #             SpectrumReducer.spectr_id == spectrum_id
        #         )
        #     ).first()
        #     if external_reducer is not None:
        #         spec_dict["external_reducer"] = external_reducer.external_reducer
        #
        #     external_observer = session.scalars(
        #         SpectrumObserver.select(session.user_or_token).where(
        #             SpectrumObserver.spectr_id == spectrum_id
        #         )
        #     ).first()
        #     if external_observer is not None:
        #         spec_dict["external_observer"] = external_observer.external_observer
        #
        #     tns_headers = {
        #         "User-Agent": f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
        #     }
        #
        #     tns_prefix, tns_name = get_IAUname(
        #         spectrum.obj.id, altdata["api_key"], tns_headers
        #     )
        #     if tns_name is None:
        #         return self.error("TNS name missing... please first post to TNS.")
        #
        #     if spectrum.obj.redshift:
        #         redshift = spectrum.obj.redshift
        #
        #     spectype_id = ["object", "host", "sky", "arcs", "synthetic"].index(
        #         spectrum_type
        #     ) + 1
        #
        #     if spec_dict["altdata"] is not None:
        #         header = spec_dict["altdata"]
        #         exposure_time = header["EXPTIME"]
        #     else:
        #         exposure_time = None
        #
        #     wav = spec_dict["wavelengths"]
        #     flux = spec_dict["fluxes"]
        #     err = spec_dict["errors"]
        #
        #     filename = f"{spectrum.instrument.name}.{spectrum_id}"
        #     filetype = "ascii"
        #
        #     with tempfile.NamedTemporaryFile(
        #         prefix=filename,
        #         suffix=f".{filetype}",
        #         mode="w",
        #     ) as f:
        #         if err is not None:
        #             for i in range(len(wav)):
        #                 f.write(f"{wav[i]} \t {flux[i]} \t {err[i]} \n")
        #         else:
        #             for i in range(len(wav)):
        #                 f.write(f"{wav[i]} \t {flux[i]}\n")
        #         f.flush()
        #
        #         data = {"api_key": altdata["api_key"]}
        #
        #         if filetype == "ascii":
        #             files = [("files[]", (filename, open(f.name), "text/plain"))]
        #         elif filetype == "fits":
        #             files = [
        #                 ("files[0]", (filename, open(f.name, "rb"), "application/fits"))
        #             ]
        #
        #         r = requests.post(
        #             upload_url, headers=tns_headers, data=data, files=files
        #         )
        #         if r.status_code != 200:
        #             return self.error(f"{r.content}")
        #
        #         spectrumdict = {
        #             "instrumentid": spectrum.instrument.tns_id,
        #             "observer": spec_dict["observers"],
        #             "reducer": spec_dict["reducers"],
        #             "spectypeid": spectype_id,
        #             "ascii_file": filename,
        #             "fits_file": "",
        #             "remarks": spectrum_comment,
        #             "spec_proprietary_period": 0.0,
        #             "obsdate": spec_dict["observed_at"],
        #         }
        #         if exposure_time is not None:
        #             spectrumdict["exptime"] = exposure_time
        #
        #         classification_report = {
        #             "name": tns_name,
        #             "classifier": classifiers,
        #             "objtypeid": classificationID,
        #             "groupid": tnsrobot.source_group_id,
        #             "remarks": classification_comment,
        #             "spectra": {"spectra-group": {"0": spectrumdict}},
        #         }
        #         if redshift is not None:
        #             classification_report["redshift"] = redshift
        #
        #         classificationdict = {
        #             "classification_report": {"0": classification_report}
        #         }
        #
        #         data = {
        #             "api_key": altdata["api_key"],
        #             "data": json.dumps(classificationdict),
        #         }
        #
        #         r = requests.post(report_url, headers=tns_headers, data=data)
        #         if r.status_code == 200:
        #             tns_id = r.json()["data"]["report_id"]
        #             return self.success(data={"tns_id": tns_id})
        #         else:
        #             return self.error(f"{r.content}")
