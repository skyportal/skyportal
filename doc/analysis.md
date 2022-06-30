# Analysis

SkyPortal serves largely as a central place of record for astronomical data and as an interaction portal around such data. Whenever advanced analysis is needed on individual sources or groups of sources the standard procedure is for end users to download the relevant data, process this data offline, and then write back results as comments or annotations.

There are a few exceptions where SkyPortal does provide in-app analysis, namely interactive periodogram analysis for variable sources (visible from the photometry panel on the source page) and `PhotStats` (a table that accumulates basic photometry statistics on on sources, accessible via API).

## External Analysis Services

SkyPortal will soon enable the establishment of 3rd party analysis services, which can be interacted with both programmatically and via the webapp. The basic idea is that data available to a user on a particular source can be sent externally (via POST request) for processing. The results of this processing are written back to SP asynchronously via a webhook. Those results can be displayed and queried in the webapp.

Some example use cases contemplated:

  - send a source to a 3rd party application which applies custom machine learning models to determine **classification** of that source
  - **Light curve fitting** to template models
  - **Redshift fitting** on spectra

### Creating a new Analysis Service

The first step is to tell SkyPortal where your analysis service lives (URL/port), what data it expects, what type of analysis it performs, etc.

```python
import requests

payload = {
    "name": "My Awesome RR Lyrae Fitter",
    "display_name": "My display name",
    "description": "We fit RRLyrae to templates",
    "version": "1.0"
    "contact_name": "I. M. Astronomer",
    "url": "http://amazing.analysis.edu:6801/analysis/rrl_analysis",
    "authentication_type": "header_token",
    "_authinfo": '{"header_token": {"Authorization": "Bearer MY_TOKEN"}}',
    "analysis_type": "lightcurve_fitting",
    "input_data_types": ["photometry", "redshift"],
    "optional_analysis_parameters": '{"rrl_type": ["ab", "c", "d", "e"}',
    'timeout': 60,
    "group_ids": [2, 4, 9]
}

header =  {'Authorization': 'token <token>'}
url = "http://localhost:5000/api/analysis_service"
r = requests.post(url, headers=header, json= payload)
analysis_id =  r.json()['data']['id']
```
We support header-based authentication and those authentications described in the `requests` package. You can also GET parameters of an analysis by ID and also modify (PATCH) and delete analyses.

### Starting a new Analysis

To kick off a new analysis on a source using a known `analysis_id`:

```
header =  {'Authorization': 'token <token>'}
url = f"http://localhost:5000/api/obj/{source_id}/analysis/{analysis_id}"
r = requests.post(url, headers=header)
```
This will assemble data on that source and send it to the 3rd party application host at the url specified when making the analysis service. It will also send a callback URL for the analysis service to send results over. This data will be stored by SkyPortal.

### What an Analysis Service returns

When a new analysis has completed it must post back the results as a JSON body to SkyPortal using the unique token embedded in the webhook URL (`callback_url`, e.g. `https://<skyportal_base>:5000/api/webhook/obj_analysis/555ce6d4-15cf...`).
The JSON response should have three keywords:

```python
("status",  "message", "analysis")
```

The webbook API looks for `status=="success"` to determine if the analysis should be considered a success or not; it's up to the analysis service to determine if the results should be considered trustworthy or not.

The "analysis" value should itself be an object containing some combination of three keywords:

```python
("inference_data", "plots", "results")
```

The "analysis" can also be empty an empty object. Theses values are used in the following way:

 - **interfence_data** - an [`arviz` InferenceData](https://arviz-devs.github.io) object, containing at least a `posterior` group.
 - **plots** - a list of plots (e.g. in png format) to be stored/shown.
 - **results** - a freeform python object containing fitting results, such as best fit parameters, goodness-of-fit results, etc. This object should be packaged on the analysis end with `joblib.dump`.

All three of these data are encoded with `base64.b64encode` to facilitate the web transport from the service to SkyPortal. Stored data can be retrieved from SkyPortal with a GET request with the flag `includeAnalysisData=True` like:

```
url = https://<skyportal_base>:5000/api/obj/analysis/<int>?includeAnalysisData=True`
r = requests.get(url, headers=<token info>)
data = r.json()
```
So that the inference data can be retrieved
like:

```python
import arviz
f = open("tmp.nc", "wb")
f.write(base64.b64decode(data["analysis"]["inference_data"]["data"]))
f.close()
inference_data = arviz.from_netcdf("tmp.nc")
```
The plots can be retrieved like:

```python
for i, plot in enumerate(data["analysis"]["plots"]):
	f = open(f"tmp_{i}.{plot["type"]}", "wb")
	f.write(base64.b64decode(plot["data"]))
	f.close()
```
And the results data can be retrieved like:

```python
import joblib
results = joblib.load(base64.b64decode(data["analysis"]["results"]["data"]))
```

A valid POST will immediately invalidate the unique token so that analysis entry cannot be posted to again (the user can simply restart an analysis with different parameters if they wish).


### Supernova Fitter Example

SkyPortal ships with an example 3rd party analysis app to fit lightcurves with supernova models in `sncosmo` (see `services/sn_analysis_service/`). To use it locally, load the demo data to create an analysis service entry that establishes the SN fitter microservice:

```
make load_demo_data
```

Then start an analysis on a source like (in Python):

```python
import requests

header =  {'Authorization': 'token <token>'}
url = "http://localhost:5000/api/obj/ZTF21aaqjmps/analysis/1"
params = {"url_parameters": {"source": "nugent-sn2p"}}
r = requests.post(url, headers=header, json=params)
```

Get the results

```
url = f"http://localhost:5000/api/obj/analysis/{r["data"]["id"]}?includeAnalysisData=True"
r = requests.get(url, headers=<token info>)
data = r.json()
```
