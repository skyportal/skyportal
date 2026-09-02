"""Client construction."""

from __future__ import annotations

from typing import Any

import httpx

from skyportal_py import (
    acls,
    allocations,
    analysis,
    annotations,
    assignments,
    brokers,
    candidates,
    catalog_queries,
    classifications,
    comments,
    earthquakes,
    filters,
    followup_requests,
    galaxies,
    gcn_events,
    group_admission_requests,
    groups,
    healpix,
    instruments,
    invitations,
    listings,
    localizations,
    mmadetectors,
    moving_objects,
    news_feed,
    objs,
    observation_plans,
    observations,
    observing_runs,
    photometric_series,
    photometry,
    profile,
    public_pages,
    recurring_apis,
    reminders,
    roles,
    sharing,
    sharing_services,
    shifts,
    skymap_triggers,
    source_groups,
    sources,
    spatial_catalogs,
    spectra,
    streams,
    summary_query,
    survey_efficiency,
    system,
    tags,
    taxonomies,
    teams,
    telescopes,
    thumbnails,
    tokens,
    users,
    weather,
)


class SkyPortal(httpx.Client):
    """An ``httpx.Client`` with the typed endpoint functions bound as methods.

    Endpoint functions take the client as their first argument, so assigning
    them here turns them into methods (``self`` is the client). Both spellings
    work: ``client.fetch_source("ZTF...")`` and
    ``sources.fetch_source(client, "ZTF...")``.
    """

    fetch_acls = acls.fetch_acls
    post_user_acl = acls.post_user_acl
    delete_user_acl = acls.delete_user_acl
    fetch_allocations = allocations.fetch_allocations
    fetch_allocation = allocations.fetch_allocation
    post_allocation = allocations.post_allocation
    update_allocation = allocations.update_allocation
    delete_allocation = allocations.delete_allocation
    fetch_allocation_report = allocations.fetch_allocation_report
    fetch_analysis_service = analysis.fetch_analysis_service
    fetch_analysis_services = analysis.fetch_analysis_services
    post_analysis_service = analysis.post_analysis_service
    update_analysis_service = analysis.update_analysis_service
    delete_analysis_service = analysis.delete_analysis_service
    fetch_default_analysis = analysis.fetch_default_analysis
    fetch_default_analyses = analysis.fetch_default_analyses
    post_default_analysis = analysis.post_default_analysis
    update_default_analysis = analysis.update_default_analysis
    delete_default_analysis = analysis.delete_default_analysis
    post_analysis = analysis.post_analysis
    fetch_analysis = analysis.fetch_analysis
    fetch_analyses = analysis.fetch_analyses
    delete_analysis = analysis.delete_analysis
    post_analysis_upload = analysis.post_analysis_upload
    fetch_analysis_results = analysis.fetch_analysis_results
    fetch_analysis_plot = analysis.fetch_analysis_plot
    fetch_annotations = annotations.fetch_annotations
    post_annotation = annotations.post_annotation
    update_annotation = annotations.update_annotation
    delete_annotation = annotations.delete_annotation
    fetch_annotation = annotations.fetch_annotation
    post_gaia_annotation = annotations.post_gaia_annotation
    post_irsa_annotation = annotations.post_irsa_annotation
    post_vizier_annotation = annotations.post_vizier_annotation
    post_datalab_annotation = annotations.post_datalab_annotation
    post_ps1_annotation = annotations.post_ps1_annotation
    fetch_assignment = assignments.fetch_assignment
    fetch_assignments = assignments.fetch_assignments
    post_assignment = assignments.post_assignment
    update_assignment = assignments.update_assignment
    delete_assignment = assignments.delete_assignment
    fetch_brokers = brokers.fetch_brokers
    fetch_broker = brokers.fetch_broker
    post_broker = brokers.post_broker
    update_broker = brokers.update_broker
    delete_broker = brokers.delete_broker
    fetch_broker_alerts = brokers.fetch_broker_alerts
    fetch_broker_alert = brokers.fetch_broker_alert
    fetch_broker_cutouts = brokers.fetch_broker_cutouts
    fetch_broker_photometry = brokers.fetch_broker_photometry
    fetch_broker_survey_photometry = brokers.fetch_broker_survey_photometry
    post_broker_alert_save = brokers.post_broker_alert_save
    fetch_broker_cone_search = brokers.fetch_broker_cone_search
    fetch_broker_filters = brokers.fetch_broker_filters
    fetch_broker_filter = brokers.fetch_broker_filter
    post_broker_filter = brokers.post_broker_filter
    update_broker_filter = brokers.update_broker_filter
    delete_broker_filter = brokers.delete_broker_filter
    fetch_broker_filter_catalog = brokers.fetch_broker_filter_catalog
    post_broker_filter_attach = brokers.post_broker_filter_attach
    post_broker_filter_test = brokers.post_broker_filter_test
    post_broker_filter_validation = brokers.post_broker_filter_validation
    fetch_broker_filter_modules = brokers.fetch_broker_filter_modules
    fetch_broker_filter_module = brokers.fetch_broker_filter_module
    post_broker_filter_module = brokers.post_broker_filter_module
    update_broker_filter_module = brokers.update_broker_filter_module
    fetch_candidate = candidates.fetch_candidate
    candidate_exists = candidates.candidate_exists
    fetch_candidates = candidates.fetch_candidates
    post_candidate = candidates.post_candidate
    delete_candidate = candidates.delete_candidate
    bulk_delete_candidates = candidates.bulk_delete_candidates
    fetch_candidates_filter = candidates.fetch_candidates_filter
    post_scan_report = candidates.post_scan_report
    fetch_scan_reports = candidates.fetch_scan_reports
    fetch_scan_report_items = candidates.fetch_scan_report_items
    update_scan_report_item = candidates.update_scan_report_item
    post_catalog_query = catalog_queries.post_catalog_query
    post_swift_lsxps_query = catalog_queries.post_swift_lsxps_query
    post_gaia_alerts_query = catalog_queries.post_gaia_alerts_query
    fetch_classifications = classifications.fetch_classifications
    post_classification = classifications.post_classification
    post_classifications = classifications.post_classifications
    delete_classification = classifications.delete_classification
    fetch_classification = classifications.fetch_classification
    fetch_classifications_query = classifications.fetch_classifications_query
    update_classification = classifications.update_classification
    delete_source_classifications = classifications.delete_source_classifications
    post_classification_vote = classifications.post_classification_vote
    delete_classification_vote = classifications.delete_classification_vote
    fetch_sources_by_classification = classifications.fetch_sources_by_classification
    fetch_comments = comments.fetch_comments
    post_comment = comments.post_comment
    update_comment = comments.update_comment
    delete_comment = comments.delete_comment
    fetch_comment = comments.fetch_comment
    post_comment_with_attachment = comments.post_comment_with_attachment
    fetch_comment_attachment = comments.fetch_comment_attachment
    fetch_comment_attachment_pdf = comments.fetch_comment_attachment_pdf
    fetch_comment_attachment_text = comments.fetch_comment_attachment_text
    fetch_comment_attachment_counts = comments.fetch_comment_attachment_counts
    post_comment_attachment_batch = comments.post_comment_attachment_batch
    fetch_earthquake = earthquakes.fetch_earthquake
    fetch_earthquakes = earthquakes.fetch_earthquakes
    fetch_earthquake_statuses = earthquakes.fetch_earthquake_statuses
    post_earthquake = earthquakes.post_earthquake
    delete_earthquake = earthquakes.delete_earthquake
    post_earthquake_prediction = earthquakes.post_earthquake_prediction
    fetch_earthquake_measurement = earthquakes.fetch_earthquake_measurement
    post_earthquake_measurement = earthquakes.post_earthquake_measurement
    update_earthquake_measurement = earthquakes.update_earthquake_measurement
    delete_earthquake_measurement = earthquakes.delete_earthquake_measurement
    fetch_filters = filters.fetch_filters
    fetch_filter = filters.fetch_filter
    post_filter = filters.post_filter
    update_filter = filters.update_filter
    delete_filter = filters.delete_filter
    fetch_followup_request = followup_requests.fetch_followup_request
    fetch_followup_requests = followup_requests.fetch_followup_requests
    post_followup_request = followup_requests.post_followup_request
    delete_followup_request = followup_requests.delete_followup_request
    update_followup_request = followup_requests.update_followup_request
    post_followup_request_comment = followup_requests.post_followup_request_comment
    post_followup_request_watcher = followup_requests.post_followup_request_watcher
    delete_followup_request_watcher = followup_requests.delete_followup_request_watcher
    fetch_followup_request_schedule = followup_requests.fetch_followup_request_schedule
    update_followup_request_prioritization = (
        followup_requests.update_followup_request_prioritization
    )
    fetch_default_followup_request = followup_requests.fetch_default_followup_request
    fetch_default_followup_requests = followup_requests.fetch_default_followup_requests
    post_default_followup_request = followup_requests.post_default_followup_request
    delete_default_followup_request = followup_requests.delete_default_followup_request
    request_followup_photometry = followup_requests.request_followup_photometry
    post_facility_message = followup_requests.post_facility_message
    fetch_galaxies = galaxies.fetch_galaxies
    fetch_galaxy_catalogs = galaxies.fetch_galaxy_catalogs
    post_galaxy_catalog = galaxies.post_galaxy_catalog
    delete_galaxy_catalog = galaxies.delete_galaxy_catalog
    post_galaxy_catalog_ascii = galaxies.post_galaxy_catalog_ascii
    post_galaxy_catalog_regalade = galaxies.post_galaxy_catalog_regalade
    post_galaxy_catalog_ned = galaxies.post_galaxy_catalog_ned
    post_gcn_event = gcn_events.post_gcn_event
    fetch_gcn_event = gcn_events.fetch_gcn_event
    fetch_gcn_events = gcn_events.fetch_gcn_events
    delete_gcn_event = gcn_events.delete_gcn_event
    post_gcn_event_alias = gcn_events.post_gcn_event_alias
    delete_gcn_event_alias = gcn_events.delete_gcn_event_alias
    fetch_gcn_event_tags = gcn_events.fetch_gcn_event_tags
    post_gcn_event_tag = gcn_events.post_gcn_event_tag
    delete_gcn_event_tag = gcn_events.delete_gcn_event_tag
    fetch_gcn_event_properties = gcn_events.fetch_gcn_event_properties
    fetch_gcn_event_survey_efficiency = gcn_events.fetch_gcn_event_survey_efficiency
    fetch_gcn_event_observation_plan_requests = (
        gcn_events.fetch_gcn_event_observation_plan_requests
    )
    fetch_gcn_event_catalog_queries = gcn_events.fetch_gcn_event_catalog_queries
    post_gcn_event_user = gcn_events.post_gcn_event_user
    delete_gcn_event_user = gcn_events.delete_gcn_event_user
    fetch_gcn_event_notice_download = gcn_events.fetch_gcn_event_notice_download
    post_gcn_event_gracedb = gcn_events.post_gcn_event_gracedb
    post_gcn_event_tach = gcn_events.post_gcn_event_tach
    fetch_gcn_event_tach = gcn_events.fetch_gcn_event_tach
    fetch_gcn_event_crossmatch = gcn_events.fetch_gcn_event_crossmatch
    post_gcn_event_crossmatch = gcn_events.post_gcn_event_crossmatch
    fetch_gcn_event_instrument_fields = gcn_events.fetch_gcn_event_instrument_fields
    fetch_gcn_event_triggers = gcn_events.fetch_gcn_event_triggers
    update_gcn_event_trigger = gcn_events.update_gcn_event_trigger
    delete_gcn_event_trigger = gcn_events.delete_gcn_event_trigger
    post_gcn_summary = gcn_events.post_gcn_summary
    fetch_gcn_summary = gcn_events.fetch_gcn_summary
    update_gcn_summary = gcn_events.update_gcn_summary
    delete_gcn_summary = gcn_events.delete_gcn_summary
    post_gcn_report = gcn_events.post_gcn_report
    fetch_gcn_reports = gcn_events.fetch_gcn_reports
    fetch_gcn_report = gcn_events.fetch_gcn_report
    update_gcn_report = gcn_events.update_gcn_report
    delete_gcn_report = gcn_events.delete_gcn_report
    post_default_gcn_tag = gcn_events.post_default_gcn_tag
    fetch_default_gcn_tag = gcn_events.fetch_default_gcn_tag
    fetch_default_gcn_tags = gcn_events.fetch_default_gcn_tags
    delete_default_gcn_tag = gcn_events.delete_default_gcn_tag
    fetch_gcn_event_sources = gcn_events.fetch_gcn_event_sources
    fetch_gcn_event_source = gcn_events.fetch_gcn_event_source
    post_gcn_event_source = gcn_events.post_gcn_event_source
    update_gcn_event_source = gcn_events.update_gcn_event_source
    delete_gcn_event_source = gcn_events.delete_gcn_event_source
    fetch_gcn_events_associated_with_source = (
        gcn_events.fetch_gcn_events_associated_with_source
    )
    post_gcn_event_obj_crossmatch = gcn_events.post_gcn_event_obj_crossmatch
    fetch_group_admission_request = (
        group_admission_requests.fetch_group_admission_request
    )
    fetch_group_admission_requests = (
        group_admission_requests.fetch_group_admission_requests
    )
    post_group_admission_request = group_admission_requests.post_group_admission_request
    update_group_admission_request = (
        group_admission_requests.update_group_admission_request
    )
    delete_group_admission_request = (
        group_admission_requests.delete_group_admission_request
    )
    fetch_groups = groups.fetch_groups
    fetch_groups_by_name = groups.fetch_groups_by_name
    fetch_group = groups.fetch_group
    post_group = groups.post_group
    update_group = groups.update_group
    delete_group = groups.delete_group
    fetch_public_group = groups.fetch_public_group
    post_group_stream = groups.post_group_stream
    delete_group_stream = groups.delete_group_stream
    post_group_user = groups.post_group_user
    update_group_user = groups.update_group_user
    delete_group_user = groups.delete_group_user
    post_group_users_from_groups = groups.post_group_users_from_groups
    fetch_healpix_counts = healpix.fetch_healpix_counts
    post_healpix_update = healpix.post_healpix_update
    fetch_instruments = instruments.fetch_instruments
    fetch_instrument = instruments.fetch_instrument
    post_instrument = instruments.post_instrument
    update_instrument = instruments.update_instrument
    delete_instrument = instruments.delete_instrument
    delete_instrument_fields = instruments.delete_instrument_fields
    fetch_instrument_logs = instruments.fetch_instrument_logs
    post_instrument_log = instruments.post_instrument_log
    fetch_instrument_log_external_api = instruments.fetch_instrument_log_external_api
    update_instrument_status = instruments.update_instrument_status
    fetch_invitations = invitations.fetch_invitations
    post_invitation = invitations.post_invitation
    update_invitation = invitations.update_invitation
    delete_invitation = invitations.delete_invitation
    fetch_listings = listings.fetch_listings
    post_listing = listings.post_listing
    update_listing = listings.update_listing
    delete_listing = listings.delete_listing
    delete_listing_by_name = listings.delete_listing_by_name
    fetch_localization = localizations.fetch_localization
    delete_localization = localizations.delete_localization
    post_localization_from_notice = localizations.post_localization_from_notice
    fetch_localization_skymap = localizations.fetch_localization_skymap
    fetch_localization_tags = localizations.fetch_localization_tags
    fetch_localization_properties = localizations.fetch_localization_properties
    fetch_localization_crossmatch = localizations.fetch_localization_crossmatch
    fetch_localization_observability_plot = (
        localizations.fetch_localization_observability_plot
    )
    fetch_localization_airmass_chart = localizations.fetch_localization_airmass_chart
    fetch_localization_worldmap_plot = localizations.fetch_localization_worldmap_plot
    fetch_mmadetector = mmadetectors.fetch_mmadetector
    fetch_mmadetectors = mmadetectors.fetch_mmadetectors
    post_mmadetector = mmadetectors.post_mmadetector
    update_mmadetector = mmadetectors.update_mmadetector
    delete_mmadetector = mmadetectors.delete_mmadetector
    fetch_mmadetector_spectrum = mmadetectors.fetch_mmadetector_spectrum
    fetch_mmadetector_spectra = mmadetectors.fetch_mmadetector_spectra
    post_mmadetector_spectrum = mmadetectors.post_mmadetector_spectrum
    update_mmadetector_spectrum = mmadetectors.update_mmadetector_spectrum
    delete_mmadetector_spectrum = mmadetectors.delete_mmadetector_spectrum
    fetch_mmadetector_time_interval = mmadetectors.fetch_mmadetector_time_interval
    fetch_mmadetector_time_intervals = mmadetectors.fetch_mmadetector_time_intervals
    post_mmadetector_time_intervals = mmadetectors.post_mmadetector_time_intervals
    update_mmadetector_time_interval = mmadetectors.update_mmadetector_time_interval
    delete_mmadetector_time_interval = mmadetectors.delete_mmadetector_time_interval
    post_moving_object_followup = moving_objects.post_moving_object_followup
    fetch_news_feed = news_feed.fetch_news_feed
    delete_obj = objs.delete_obj
    fetch_obj_position = objs.fetch_obj_position
    post_super_obj = objs.post_super_obj
    fetch_super_obj = objs.fetch_super_obj
    fetch_super_objs = objs.fetch_super_objs
    update_super_obj = objs.update_super_obj
    delete_super_obj = objs.delete_super_obj
    fetch_unsourced_finding_chart = objs.fetch_unsourced_finding_chart
    post_observation_plan = observation_plans.post_observation_plan
    post_observation_plans = observation_plans.post_observation_plans
    fetch_observation_plan = observation_plans.fetch_observation_plan
    fetch_observation_plans = observation_plans.fetch_observation_plans
    delete_observation_plan = observation_plans.delete_observation_plan
    post_observation_plan_manual = observation_plans.post_observation_plan_manual
    fetch_observation_plan_names = observation_plans.fetch_observation_plan_names
    fetch_observation_plan_name_exists = (
        observation_plans.fetch_observation_plan_name_exists
    )
    post_observation_plan_treasuremap = (
        observation_plans.post_observation_plan_treasuremap
    )
    delete_observation_plan_treasuremap = (
        observation_plans.delete_observation_plan_treasuremap
    )
    fetch_observation_plan_gcn = observation_plans.fetch_observation_plan_gcn
    post_observation_plan_queue = observation_plans.post_observation_plan_queue
    delete_observation_plan_queue = observation_plans.delete_observation_plan_queue
    fetch_observation_plan_movie = observation_plans.fetch_observation_plan_movie
    fetch_observation_plan_simsurvey = (
        observation_plans.fetch_observation_plan_simsurvey
    )
    delete_observation_plan_simsurvey = (
        observation_plans.delete_observation_plan_simsurvey
    )
    fetch_observation_plan_simsurvey_plot = (
        observation_plans.fetch_observation_plan_simsurvey_plot
    )
    fetch_observation_plan_geojson = observation_plans.fetch_observation_plan_geojson
    fetch_observation_plan_survey_efficiency = (
        observation_plans.fetch_observation_plan_survey_efficiency
    )
    post_observation_plan_observing_run = (
        observation_plans.post_observation_plan_observing_run
    )
    delete_observation_plan_fields = observation_plans.delete_observation_plan_fields
    post_default_observation_plan = observation_plans.post_default_observation_plan
    fetch_default_observation_plan = observation_plans.fetch_default_observation_plan
    fetch_default_observation_plans = observation_plans.fetch_default_observation_plans
    delete_default_observation_plan = observation_plans.delete_default_observation_plan
    fetch_allocation_observation_plans = (
        observation_plans.fetch_allocation_observation_plans
    )
    fetch_observations = observations.fetch_observations
    post_observation = observations.post_observation
    delete_observation = observations.delete_observation
    post_observation_ascii = observations.post_observation_ascii
    fetch_observation_simsurvey = observations.fetch_observation_simsurvey
    delete_observation_simsurvey = observations.delete_observation_simsurvey
    fetch_observation_simsurvey_plot = observations.fetch_observation_simsurvey_plot
    post_observation_treasuremap = observations.post_observation_treasuremap
    delete_observation_treasuremap = observations.delete_observation_treasuremap
    post_observation_external_api = observations.post_observation_external_api
    fetch_observation_external_api = observations.fetch_observation_external_api
    delete_observation_external_api = observations.delete_observation_external_api
    fetch_observing_runs = observing_runs.fetch_observing_runs
    fetch_observing_run = observing_runs.fetch_observing_run
    post_observing_run = observing_runs.post_observing_run
    delete_observing_run = observing_runs.delete_observing_run
    update_observing_run = observing_runs.update_observing_run
    update_observing_run_not_observed = observing_runs.update_observing_run_not_observed
    fetch_photometric_series = photometric_series.fetch_photometric_series
    fetch_photometric_series_page = photometric_series.fetch_photometric_series_page
    post_photometric_series = photometric_series.post_photometric_series
    update_photometric_series = photometric_series.update_photometric_series
    delete_photometric_series = photometric_series.delete_photometric_series
    fetch_photometry = photometry.fetch_photometry
    post_photometry = photometry.post_photometry
    upsert_photometry = photometry.upsert_photometry
    fetch_photometry_point = photometry.fetch_photometry_point
    delete_photometry = photometry.delete_photometry
    update_photometry = photometry.update_photometry
    fetch_photometry_range = photometry.fetch_photometry_range
    fetch_photometry_origins = photometry.fetch_photometry_origins
    bulk_delete_photometry = photometry.bulk_delete_photometry
    post_photometry_validation = photometry.post_photometry_validation
    update_photometry_validation = photometry.update_photometry_validation
    delete_photometry_validation = photometry.delete_photometry_validation
    fetch_profile = profile.fetch_profile
    update_profile = profile.update_profile
    fetch_public_source_pages = public_pages.fetch_public_source_pages
    post_public_source_page = public_pages.post_public_source_page
    delete_public_source_page = public_pages.delete_public_source_page
    fetch_public_releases = public_pages.fetch_public_releases
    post_public_release = public_pages.post_public_release
    update_public_release = public_pages.update_public_release
    delete_public_release = public_pages.delete_public_release
    fetch_recurring_apis = recurring_apis.fetch_recurring_apis
    fetch_recurring_api = recurring_apis.fetch_recurring_api
    post_recurring_api = recurring_apis.post_recurring_api
    delete_recurring_api = recurring_apis.delete_recurring_api
    fetch_reminders = reminders.fetch_reminders
    fetch_reminder = reminders.fetch_reminder
    post_reminder = reminders.post_reminder
    update_reminder = reminders.update_reminder
    delete_reminder = reminders.delete_reminder
    fetch_roles = roles.fetch_roles
    post_user_role = roles.post_user_role
    delete_user_role = roles.delete_user_role
    post_sharing = sharing.post_sharing
    fetch_sharing_services = sharing_services.fetch_sharing_services
    fetch_sharing_service = sharing_services.fetch_sharing_service
    post_sharing_service = sharing_services.post_sharing_service
    update_sharing_service = sharing_services.update_sharing_service
    delete_sharing_service = sharing_services.delete_sharing_service
    post_sharing_service_submission = sharing_services.post_sharing_service_submission
    fetch_sharing_service_submission = sharing_services.fetch_sharing_service_submission
    fetch_sharing_service_submissions = (
        sharing_services.fetch_sharing_service_submissions
    )
    post_sharing_service_coauthor = sharing_services.post_sharing_service_coauthor
    delete_sharing_service_coauthor = sharing_services.delete_sharing_service_coauthor
    update_sharing_service_group = sharing_services.update_sharing_service_group
    delete_sharing_service_group = sharing_services.delete_sharing_service_group
    post_sharing_service_auto_publishers = (
        sharing_services.post_sharing_service_auto_publishers
    )
    delete_sharing_service_auto_publishers = (
        sharing_services.delete_sharing_service_auto_publishers
    )
    fetch_shift = shifts.fetch_shift
    fetch_shifts = shifts.fetch_shifts
    post_shift = shifts.post_shift
    update_shift = shifts.update_shift
    delete_shift = shifts.delete_shift
    post_shift_user = shifts.post_shift_user
    update_shift_user = shifts.update_shift_user
    delete_shift_user = shifts.delete_shift_user
    fetch_shift_summary = shifts.fetch_shift_summary
    fetch_skymap_triggers = skymap_triggers.fetch_skymap_triggers
    post_skymap_trigger = skymap_triggers.post_skymap_trigger
    delete_skymap_trigger = skymap_triggers.delete_skymap_trigger
    post_source_groups = source_groups.post_source_groups
    update_source_group = source_groups.update_source_group
    fetch_source = sources.fetch_source
    source_exists = sources.source_exists
    fetch_sources = sources.fetch_sources
    fetch_sources_save_summary = sources.fetch_sources_save_summary
    post_source = sources.post_source
    update_source = sources.update_source
    delete_source = sources.delete_source
    delete_source_photometry = sources.delete_source_photometry
    fetch_source_offsets = sources.fetch_source_offsets
    fetch_source_finder = sources.fetch_source_finder
    fetch_source_finder_json = sources.fetch_source_finder_json
    fetch_finder_chart_facilities = sources.fetch_finder_chart_facilities
    post_source_host = sources.post_source_host
    delete_source_host = sources.delete_source_host
    fetch_source_saved_groups = sources.fetch_source_saved_groups
    post_source_labels = sources.post_source_labels
    delete_source_labels = sources.delete_source_labels
    fetch_source_color_mag = sources.fetch_source_color_mag
    post_source_gcn_event_crossmatch = sources.post_source_gcn_event_crossmatch
    post_source_mpc_query = sources.post_source_mpc_query
    fetch_source_tns = sources.fetch_source_tns
    fetch_source_observability = sources.fetch_source_observability
    post_source_photometry_copy = sources.post_source_photometry_copy
    fetch_source_phot_stat = sources.fetch_source_phot_stat
    post_source_phot_stat = sources.post_source_phot_stat
    update_source_phot_stat = sources.update_source_phot_stat
    delete_source_phot_stat = sources.delete_source_phot_stat
    fetch_phot_stats_counts = sources.fetch_phot_stats_counts
    post_phot_stats = sources.post_phot_stats
    update_phot_stats = sources.update_phot_stats
    fetch_phot_stats_aggregate = sources.fetch_phot_stats_aggregate
    fetch_source_exists = sources.fetch_source_exists
    post_source_notification = sources.post_source_notification
    fetch_spatial_catalog = spatial_catalogs.fetch_spatial_catalog
    fetch_spatial_catalogs = spatial_catalogs.fetch_spatial_catalogs
    post_spatial_catalog = spatial_catalogs.post_spatial_catalog
    delete_spatial_catalog = spatial_catalogs.delete_spatial_catalog
    post_spatial_catalog_ascii = spatial_catalogs.post_spatial_catalog_ascii
    fetch_spectrum = spectra.fetch_spectrum
    fetch_spectra = spectra.fetch_spectra
    post_spectrum = spectra.post_spectrum
    delete_spectrum = spectra.delete_spectrum
    update_spectrum = spectra.update_spectrum
    fetch_spectra_query = spectra.fetch_spectra_query
    fetch_spectra_range = spectra.fetch_spectra_range
    post_spectra_bulk = spectra.post_spectra_bulk
    parse_spectrum_ascii = spectra.parse_spectrum_ascii
    post_spectrum_ascii = spectra.post_spectrum_ascii
    post_synthetic_photometry = spectra.post_synthetic_photometry
    fetch_streams = streams.fetch_streams
    fetch_stream = streams.fetch_stream
    post_stream = streams.post_stream
    update_stream = streams.update_stream
    delete_stream = streams.delete_stream
    post_stream_user = streams.post_stream_user
    delete_stream_user = streams.delete_stream_user
    post_summary_query = summary_query.post_summary_query
    fetch_survey_efficiency_for_observations = (
        survey_efficiency.fetch_survey_efficiency_for_observations
    )
    fetch_survey_efficiencies_for_observations = (
        survey_efficiency.fetch_survey_efficiencies_for_observations
    )
    fetch_survey_efficiency_for_observation_plan = (
        survey_efficiency.fetch_survey_efficiency_for_observation_plan
    )
    fetch_survey_efficiencies_for_observation_plan = (
        survey_efficiency.fetch_survey_efficiencies_for_observation_plan
    )
    post_default_survey_efficiency = survey_efficiency.post_default_survey_efficiency
    fetch_default_survey_efficiency = survey_efficiency.fetch_default_survey_efficiency
    fetch_default_survey_efficiencies = (
        survey_efficiency.fetch_default_survey_efficiencies
    )
    delete_default_survey_efficiency = (
        survey_efficiency.delete_default_survey_efficiency
    )
    fetch_sysinfo = system.fetch_sysinfo
    fetch_config = system.fetch_config
    fetch_db_stats = system.fetch_db_stats
    fetch_enum_types = system.fetch_enum_types
    fetch_dbinfo = system.fetch_dbinfo
    fetch_altdata_info = system.fetch_altdata_info
    fetch_annotations_info = system.fetch_annotations_info
    fetch_obj_tag_options = tags.fetch_obj_tag_options
    post_obj_tag_option = tags.post_obj_tag_option
    update_obj_tag_option = tags.update_obj_tag_option
    delete_obj_tag_option = tags.delete_obj_tag_option
    fetch_obj_tags = tags.fetch_obj_tags
    post_obj_tag = tags.post_obj_tag
    delete_obj_tag = tags.delete_obj_tag
    fetch_taxonomies = taxonomies.fetch_taxonomies
    fetch_taxonomy = taxonomies.fetch_taxonomy
    post_taxonomy = taxonomies.post_taxonomy
    update_taxonomy = taxonomies.update_taxonomy
    delete_taxonomy = taxonomies.delete_taxonomy
    fetch_teams = teams.fetch_teams
    fetch_team = teams.fetch_team
    post_team = teams.post_team
    update_team = teams.update_team
    delete_team = teams.delete_team
    fetch_telescopes = telescopes.fetch_telescopes
    fetch_telescope = telescopes.fetch_telescope
    post_telescope = telescopes.post_telescope
    update_telescope = telescopes.update_telescope
    delete_telescope = telescopes.delete_telescope
    fetch_thumbnail = thumbnails.fetch_thumbnail
    post_thumbnail = thumbnails.post_thumbnail
    update_thumbnail = thumbnails.update_thumbnail
    delete_thumbnail = thumbnails.delete_thumbnail
    fetch_thumbnail_paths = thumbnails.fetch_thumbnail_paths
    update_thumbnail_paths = thumbnails.update_thumbnail_paths
    delete_thumbnail_folders = thumbnails.delete_thumbnail_folders
    fetch_tokens = tokens.fetch_tokens
    fetch_token = tokens.fetch_token
    post_token = tokens.post_token
    update_token = tokens.update_token
    delete_token = tokens.delete_token
    fetch_users = users.fetch_users
    fetch_user = users.fetch_user
    post_user = users.post_user
    update_user = users.update_user
    delete_user = users.delete_user
    fetch_weather = weather.fetch_weather


def create_client(
    base_url: str,
    token: str | None = None,
    *,
    timeout: float | None = 30.0,
    **httpx_kwargs: Any,  # noqa: ANN401 -- forwarded verbatim to httpx.Client
) -> SkyPortal:
    """Create a client configured for a SkyPortal instance.

    Reuse one client per instance: it pools connections, so repeated
    requests skip the TCP/TLS handshake.

    Parameters
    ----------
    base_url : str
        Root URL of the SkyPortal instance, e.g. ``https://fritz.science``.
    token : str, optional
        API token from your SkyPortal profile page. Omit for anonymous
        access to instances that allow it.
    timeout : float or None, optional
        Timeout in seconds applied to every request; None disables it.
    **httpx_kwargs
        Remaining ``httpx.Client`` options, e.g. ``trust_env=False`` to keep
        a netrc entry from overriding the token header.
    """
    headers = {} if token is None else {"Authorization": f"token {token}"}
    return SkyPortal(
        base_url=base_url, headers=headers, timeout=timeout, **httpx_kwargs
    )
