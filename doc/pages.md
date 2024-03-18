# Front-end Pages

Skyportal has many front-end pages to interact with the data. In the following, we enumerate these pages and the end point to which they are connected.

## Page List

Sources: This page provides filtering of available sources, including by date, sky location, photometric behavior, classification, redshift, and other metadata.
/sources/

Source: This page provides a summary of source properties, including photometry, spectroscopy, annotations, comments, and other metadata. It also allows for triggering of follow-up instruments and forced photometry.
/source/{source_id}. source_id is the id of the Source.

Group Sources: This page is similar to the Sources page, but is limited to the sources for a particular group.
/group_sources/{group_id}. group_id is the id of the Group.

Candidates: This page provides a user interface for scanning, where alerts passing a specific filter can be saved to groups as sources.
/candidates

Favorites: This page provides the list of sources that the user has denoted as a favorite, indicated by a star next to the source name.
/favorites

Alerts: This page allows for alerts to be queried by sky location within a specific radius.
/alerts

Persistent Sources: This page allows for light curves to be queried by sky location within a specific radius.
/archive

Groups Page: This page shows the existing groups a user is a member above. It also allows for group creation.
/groups/

Group Page: This page shows the existing members of a specific group. It also allows the user to add or remove members from a group, if they are a group admin. It also links to the Group Sources page.
/group/{group_id}. group_id is the id of the Group.

Observing Runs Page: This page shows information about existing observing runs. It also allows for observing run creation.
/runs/

Observing Run Page: This page summarizes the sources associated with an observing run. It also allows for the creation of standard star lists. It also allows for the creation of observing charts.
/run/{run_id}. run_id is the id of the Observing Run.

GCN Events Page: This page provides filtering of available GCN events, including by date, event alias, tag, properties, and other metadata.
/gcn_events

GCN Event Page: This page provides a summary of GCN event properties, including localizations, comments, associated sources, and other metadata. It also allows for creation of observing plans and triggering of follow-up instruments.
/gcn_events/{date} where date is the time of the event in ISOT format.

Followup Requests Page: This page provides filtering of existing follow-up requests by date, instrument, status and other metadata. It also allows for the creation of an observing schedule for active requests.
/followup_requests

Summary Search Page: This page provides natural language processing of queries related to sources.
/summary_search

About Page: This page provides information about SkyPortal, including the developers of the application, links to papers to reference and other metadata.
/about

Telescopes Page: This page provides the list of telescopes registered, including information such as their location and size. It also includes a world map showing their locations. It also allows for the creation of telescopes.
/telescopes

Instruments Page: This page provides the list of instruments registered, including information such as their type, filters, and associated telescope. It also allows for the creation of instruments.
/instruments

MMADetectors Page: This page provides a list of multi-messenger instruments registered, including their location and type. It also includes a world map showing their locations. It also allows for the creation of multi-messenger detectors.
/mmadetectors

Allocations Page: This page provides the list of follow-up allocations registered, including information such as their associated instrument, start and end date, PI, group, and admins. It also allows for the creation and modification of allocations. It also allows for the creation and modification of default follow-up plans.
/telescopes

Observations Page: This page provides filtering of observations by date, instrument, filter and other metadata. It also allows for the upload of observations through a file. It also allows for creation of automated ingestion, either for executed or queued observations. It also allows for direct interactions with telescope queues.
/observations

Galaxies Page: This page provides filtering of galaxies by catalog, position, redshift, distance, GCN event and other metadata. It also allows for the upload of galaxies through a file.
/galaxies

Spatial Catalogs Page: This page provides lists of spatial catalogs, which are designed to filter sources by spatially extended sources. It also allows for the upload of spatial catalogs through a file.
/spatial_catalogs

Analysis Services Page: This page provides the list of analysis services registered, including information such as the URL and default share groups. It also allows for the creation of analysis services.
/services

Recurring APIs Page: This page provides the list of recurring APIs registered, including information such as the API, the delay between calls and whether it is active. It also allows for the creation of recurring API calls.
/recurring_apis

Taxonomies Page: This page provides the list of taxonomies registered, including information such as the hierarchy, version and provenance. It also allows for the creation and modification of taxonomies.
/taxonomies

Database Statistics Page: This page provides a list of typical database statistics, including the number of sources, photometry points, users, and other data. This page is only accessible to administrators.
/db_stats

User Management Page: This page provides a list of users, including their name, username, email, roles, ACLs, and groups. This page also allows for the invitation of new users. This page is only accessible to administrators.
/user_management
