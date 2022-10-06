# MMA Features

Skyportal supports multi-messenger astronomy (MMA) features. In particular, we ingest events from [GCN](https://gcn.gsfc.nasa.gov/); the service controlling this is here: https://github.com/skyportal/skyportal/blob/main/skyportal/services/gcn_service/gcn_service.py.

We ingest gravitational-wave events from the International Gravitational-Wave Network (IGWN), gamma-ray burst events from Fermi Gamma-ray Burst Monitor (GBM), and neutrinos from IceCube. To each `GcnEvent` is associated a set of `Localization`s, which are HEALPix-based maps containing the probability density as a function of sky location. Each `GcnEvent` is identified by its event time, as represented in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). The `Localization`s are connected to a `GcnEvent` by this `dateobs.`

The features are available on the **gcn_events** page, where information on the events (including the skymaps), and associated triggering of follow-up is available. In particular, `Allocations` now cover both transient follow-up (as a `FollowupRequest`) and GCN event follow-up (as an `ObservationPlanRequest`). The main difference between these two is that a `FollowupRequest` is a single pointing associated with a particular object. An `ObservationPlanRequest` (which triggers an associated `EventObservationPlan` with knowledge of the particular fields, filters, and exposure times to be used) performs tiling of a `Localization.`

These `ObservationPlanRequest`s in particular are triggered on the front-end from the **gcn_events** page, with drop down menus creating a schedule for a given instrument. This request creates an `EventObservationPlan`, which will then have the option of being sent to the instrument through the APIs developed in the **FollowupRequest** (see the APIs here: https://github.com/skyportal/skyportal/tree/main/skyportal/facility_apis).

To evaluate the efficacy of the executed observation plans, we have the `ExecutedObservation`s table, which is accessible through the `observation` api. After execution of the requested observations in the `EventObservationPlan`, the user is responsible for uploading successfully executed observations to the `ExecutedObservation`s table (see below). Users should include information about the time of observation, filter, limiting magnitude, etc. The results of the observations can be compared to the `Localization`s to determine sky coverage and integrated probability contained with the map.

## Uploading executed observations

In addition to making available the `observation` api, we also include an Observations page to simplify upload and viewing of `ExecutedObservation`s. On this page, simply specify the instrument and upload a file of the form:

observation_id,field_id,obstime,seeing,limmag,exposure_time,filter,processed_fraction
84434604,1,2458598.8460417003,1.5741500000,20.4070500000,30,ztfr,1.00000
84434651,1,2458598.8465162003,1.5812000000,20.4940500000,30,ztfr,1.00000
84434696,1,2458598.8469676003,1.6499500000,20.5603000000,30,ztfr,1.00000

where observation_id (the ID of the observations, does not need to be unique), the field_id, the observation time (in JD or otherwise any unambigious format as specified in the astropy docs such as iso or isot: https://docs.astropy.org/en/stable/time/index.html), the seeing (in arcseconds), the limiting magnitude, the exposure time (in seconds), the filter, and the "processed_fraction" (what fraction of the image was successfully processed) are potential columns. We note that only observation_id, field_id, obstime, filter, and exposure_time are required.

It is also possible to upload by right ascension and declination in cases where field IDs are not available. In this case, field_id is replaced by the columns RA and Dec, i.e.

observation_id,RA,Dec,obstime,seeing,limmag,exposure_time,filter,processed_fraction
94434604,30.0,60.0,2458598.8460417003,1.5741500000,20.4070500000,30,ztfr,1.00000
94434651,45.0,45.0,2458598.8465162003,1.5812000000,20.4940500000,30,ztfr,1.00000
94434696,60.0,30.0,2458598.8469676003,1.6499500000,20.5603000000,30,ztfr,1.00000

## Executed Observations API Upload

As part of the `ObservationPlanRequest` API, it is possible to retrieve `ExecutedObservation`s. We briefly describe the authentication form the available telescopes take below:

* ZTF: Login information for IRSA, which takes the form: {"tap_service": "https://irsa.ipac.caltech.edu/TAP", "tap_username": "your_password", "tap_password": "your_password"}


## GCN Event Ingestion

We use [gcn-kafka](https://github.com/nasa-gcn/gcn-kafka-python) to ingest multi-messenger events distributed by the [General Coordinates Network (GCN)](https://gcn.nasa.gov/) within SkyPortal.

For configuration, one requires a client_id and client_secret at https://gcn.nasa.gov/quickstart. Once that is available, the configuration file should contain the following information (discuss with your administrators if someone else is deploying will be edited as the below).

```
gcn:
  server: gcn.nasa.gov
  client_id:
  client_secret:
  notice_types:
    - FERMI_GBM_FLT_POS
    - FERMI_GBM_GND_POS
    - FERMI_GBM_FIN_POS
    - FERMI_GBM_SUBTHRESH
    - LVC_PRELIMINARY
    - LVC_INITIAL
    - LVC_UPDATE
    - LVC_RETRACTION
    - AMON_ICECUBE_COINC
    - AMON_ICECUBE_HESE
    - ICECUBE_ASTROTRACK_GOLD
    - ICECUBE_ASTROTRACK_BRONZE
```

where notice types are also available from the GCN quickstart guide linked above.

## Earthquake Ingestion

The most important environmental effect on detectors in the IGWN remains teleseismic earthquakes. For this reason, we enable ingestion of earthquakes using the USGS' [PDL client](https://github.com/usgs/pdl).

In order to deploy the service, one must:
* Email Michelle Guy (mguy@usgs.gov) with the static IP address of the server and explain the tool's usage
* Download the [Product Client](https://github.com/usgs/pdl/releases/download/2.7.10/ProductClient.jar) and place it in the services/pdl_service/ directory.
* Deploy the Product Client from within services/pdl_service/ by running: ./init.sh start
