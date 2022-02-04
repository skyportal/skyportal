# MMA Features

We are beginning to add multi-messenger astronomy (MMA) features to the app. In particular, we are ingesting events from [GCN](https://gcn.gsfc.nasa.gov/); the service controlling this is here: https://github.com/skyportal/skyportal/blob/master/skyportal/services/gcn_service/gcn_service.py.

We are ingesting gravitational-wave events from the International Gravitational-Wave Network (IGWN), gamma-ray burst events from Fermi Gamma-ray Burst Monitor (GBM), and neutrinos from IceCube. To each `GcnEvent` is associated a set of `Localization`s, which are HEALPix-based maps containing the probability density as a function of sky location. Each `GcnEvent` is identified by its event time (represented in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`). The `Localization`s are connected to a `GcnEvent` by this `dateobs.`

We are building out features on the **gcn_events** page, where information on the events (including the skymaps), and associated triggering of follow-up is being made available. In particular, `Allocations` now cover both transient follow-up (as a `FollowupRequest`) and GCN event follow-up (as an `ObservationPlanRequest`). The main difference between these two is that a `FollowupRequest` is a single pointing associated with a particular object. An `ObservationPlanRequest` performs tiling of a `Localization.`

These `ObservationPlanRequest`s in particular are triggered on the front-end from the **gcn_events** page, with drop down menus creating a schedule for a given instrument. This request creates an `ObservationPlan`, which will then have the option of being sent to the instrument through the APIs developed in the **FollowupRequest** (see the APIs here: https://github.com/skyportal/skyportal/tree/master/skyportal/facility_apis).
