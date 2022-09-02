# MMA Features

Skyportal supports multi-messenger astronomy (MMA) features. In particular, we ingest events from [GCN](https://gcn.gsfc.nasa.gov/); the service controlling this is here: https://github.com/skyportal/skyportal/blob/main/skyportal/services/gcn_service/gcn_service.py.

We ingest gravitational-wave events from the International Gravitational-Wave Network (IGWN), gamma-ray burst events from Fermi Gamma-ray Burst Monitor (GBM), and neutrinos from IceCube. To each `GcnEvent` is associated a set of `Localization`s, which are HEALPix-based maps containing the probability density as a function of sky location. Each `GcnEvent` is identified by its event time, as represented in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). The `Localization`s are connected to a `GcnEvent` by this `dateobs.`

The features are available on the **gcn_events** page, where information on the events (including the skymaps), and associated triggering of follow-up is available. In particular, `Allocations` now cover both transient follow-up (as a `FollowupRequest`) and GCN event follow-up (as an `ObservationPlanRequest`). The main difference between these two is that a `FollowupRequest` is a single pointing associated with a particular object. An `ObservationPlanRequest` (which triggers an associated `EventObservationPlan` with knowledge of the particular fields, filters, and exposure times to be used) performs tiling of a `Localization.`

These `ObservationPlanRequest`s in particular are triggered on the front-end from the **gcn_events** page, with drop down menus creating a schedule for a given instrument. This request creates an `EventObservationPlan`, which will then have the option of being sent to the instrument through the APIs developed in the **FollowupRequest** (see the APIs here: https://github.com/skyportal/skyportal/tree/main/skyportal/facility_apis).

To evaluate the efficacy of the executed observation plans, we have the `ExecutedObservation`s table, which is accessible through the `observation` api. After execution of the requested observations in the `EventObservationPlan`, the user is responsible for uploading successfully executed observations to the `ExecutedObservation`s table (see below). Users should include information about the time of observation, filter, limiting magnitude, etc. The results of the observations can be compared to the `Localization`s to determine sky coverage and integrated probability contained with the map.

## Follow-up triggering

The vast majority of follow-up instruments will require some form of authentication. All such information is passed through the `altdata` variable of the `Allocation`s API. We briefly describe the authentication form the available telescopes take below:

* ATLAS Forced Photometry: A user account must be made on https://fallingstar-data.com/forcedphot/, at which point the authentication takes the form `{"api_token": "testtoken"}`.
* KAIT: A username and password are passed as `{"username": "username", "password": "password"}`.
* LCO: A user account must be made on https://lco.global/, at which point the authentication takes the form `{"PROPOSAL_ID": "your_proposal_ID", "API_TOKEN": "testtoken", "API_ARCHIVE_TOKEN": "testarchivetoken"}`. The submission token is available directly from https://observe.lco.global while the archive token can be aquired by API:
ar = requests.post('https://archive-api.lco.global/api-token-auth/',
                       data = {'username': username, 'password': password})
ar_token = ar.json()['token']
* LT: A proposal ID, username, and password are passed as `{"username": "username", "password": "password", "LT_proposalID": "your_proposal_ID"}`.
* SLACK: As discussed further [here](./slack.html), slack information is pass as `{"slack_workspace": "XXX", "slack_channel": "YYY", "slack_token": "ZZZ"}`.
* SWIFT Triggering: A username and password are passed as `{"username": "username", "secret": "password"}`.
* SWIFT XRT Reductions: A user account must be made with the Swift-XRT data products API platform (see https://www.swift.ac.uk/user_objects/register.php to register). The authentication then is the email of the user `"XRT_UserID": "swift_email"}` where swift_email is the email address used upon sign up.
* ZTF Triggering: An API token for an admin user for [Kowalski](https://github.com/dmitryduev/kowalski) can be passed as `{"access_token": "your_token"}`.
* ZTF Forced Photometry: A user account must be made with the ZTF forced photometry service (see https://zwicky.tf/vgt). The authentication then takes the form `{"ipac_http_user": "http_user", "ipac_http_password": "http_password", "ipac_email": "email", "ipac_userpass": "password"}` where http_user and http_password are provided in the documentation and ipac_email and ipac_userpass are provided for the specific account. Note that IPAC's forced photometry database is updated once per hour, on the hour, and requests will only be available after this update.

## Uploading executed observations

In addition to making available the `observation` api, we also include an Observations page to simplify upload and viewing of `ExecutedObservation`s. On this page, simply specify the instrument and upload a file of the form:

observation_id,field_id,obstime,seeing,limmag,exposure_time,filter,processed_fraction
84434604,1,2458598.8460417003,1.5741500000,20.4070500000,30,ztfr,1.00000
84434651,1,2458598.8465162003,1.5812000000,20.4940500000,30,ztfr,1.00000
84434696,1,2458598.8469676003,1.6499500000,20.5603000000,30,ztfr,1.00000

where observation_id (the ID of the observations, does not need to be unique), the field_id, the observation time (in JD or otherwise any unambigious format as specified in the astropy docs such as iso or isot: https://docs.astropy.org/en/stable/time/index.html), the seeing (in arcseconds), the limiting magnitude, the exposure time (in seconds), the filter, and the "processed_fraction" (what fraction of the image was successfully processed) are potential columns. We note that only observation_id, field_id, obstime, filter, and exposure_time required.

## Executed Observations API Upload

As part of the `ObservationPlanRequest` API, it is possible to retrieve `ExecutedObservation`s. We briefly describe the authentication form the available telescopes take below:

* ZTF: Login information for IRSA, which takes the form: {"tap_service": "https://irsa.ipac.caltech.edu/TAP", "tap_username": "your_password", "tap_password": "your_password"}
