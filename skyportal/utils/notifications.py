import datetime

import json
import lxml
import requests
import sqlalchemy as sa
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.app_utils import get_app_base_url
from skyportal.models import GcnEvent
from skyportal.models.gcn import SOURCE_RADIUS_THRESHOLD

env, cfg = load_env()

app_url = get_app_base_url()

log = make_log('notifications')


def gcn_notification_content(target, session):
    dateobs = target.dateobs
    dateobs_txt = Time(dateobs).isot
    source_name = dateobs_txt.replace(":", "-")

    stmt = sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
    gcn_event = session.execute(stmt).scalars().first()

    localizations = gcn_event.localizations
    tags = []
    # get the latest localization
    localization = None
    if localizations is not None and len(localizations) > 0:
        localization = localizations[-1]
        tags = [tag.text for tag in localization.tags]

    time_since_dateobs = datetime.datetime.utcnow() - gcn_event.dateobs
    # remove the microseconds from the timedelta
    time_since_dateobs = time_since_dateobs - datetime.timedelta(
        microseconds=time_since_dateobs.microseconds
    )

    new_event = False
    if gcn_event.gcn_notices is None or len(gcn_event.gcn_notices) < 2:
        new_event = True

    notice_type = 'No notice type'
    notice_content = None
    name = None

    # get the most recent notice for this event
    if gcn_event.gcn_notices is not None and len(gcn_event.gcn_notices) > 0:
        last_gcn_notice = gcn_event.gcn_notices[-1]
        if last_gcn_notice.notice_type is not None:
            notice_type = last_gcn_notice.notice_type
        if last_gcn_notice.notice_format == "voevent":
            notice_content = lxml.etree.fromstring(last_gcn_notice.content)
            name = notice_content.find('./Why/Inference/Name')
        elif last_gcn_notice.notice_format == "json":
            notice_content = json.loads(last_gcn_notice.content.decode('utf8'))

    if name is not None:
        source_name = (name.text).replace(" ", "")
    elif 'GRB' in tags:
        # we want the name to be like GRB YYMMDD.HHMM
        source_name = f"GRB{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
    elif 'GW' in tags:
        source_name = f"GW{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"

    if notice_content is not None:
        if isinstance(notice_content, dict):
            ra = notice_content.get("ra")
            dec = notice_content.get("dec")
            error = notice_content.get("ra_dec_error")
        else:
            loc = notice_content.find('./WhereWhen/ObsDataLocation/ObservationLocation')
            ra = loc.find('./AstroCoords/Position2D/Value2/C1')
            dec = loc.find('./AstroCoords/Position2D/Value2/C2')
            error = loc.find('./AstroCoords/Position2D/Error2Radius')

            if ra is not None:
                ra = float(ra.text)
            if dec is not None:
                dec = float(dec.text)
            if error is not None:
                error = float(error.text)
    else:
        ra = None
        dec = None
        error = None

    aliases = gcn_event.aliases
    links = {}
    # look if there are aliases with LVC prefix, or Fermi prefix
    for alias in aliases:
        if alias.startswith('LVC'):
            name = alias.split('#')[1]
            links['LVC'] = f"https://gracedb.ligo.org/superevents/{name}/view/"
        if alias.startswith('Fermi'):
            # get the current year
            name = alias.split('#')[1]
            year = datetime.datetime.now().year
            links[
                'Fermi'
            ] = f"https://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/triggers/{year}/{name}/quicklook/"

    return {
        'dateobs': dateobs_txt,
        'source_name': source_name,
        'notice_type': notice_type,
        'new_event': new_event,
        'time_since_dateobs': time_since_dateobs,
        'ra': ra,
        'dec': dec,
        'error': error,
        'tags': tags,
        'links': links,
        'app_url': app_url,
        'localization_name': localization.localization_name if localization else None,
    }


def gcn_slack_notification(target, data=None, new_tag=False):
    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

    if data['new_event']:
        header_text = f"New Event: <{app_url}{target['url']}|*{data['dateobs']}*> ({data['notice_type']})"
    elif new_tag:
        header_text = f"New tag added to Event: <{app_url}{target['url']}|*{data['dateobs']}*> ({data['notice_type']})"
    else:
        header_text = f"New notice for Event: <{app_url}{target['url']}|*{data['dateobs']}*> ({data['notice_type']})"

    time_text = f"*Time*:\n *-* Trigger Time (T0): {data['dateobs']}\n *-* Time since T0: {data['time_since_dateobs']}"
    notice_type_text = f"*Notice Type*: {data['notice_type']}"

    if data['ra'] is not None and data['dec'] is not None and data['error'] is not None:
        # the event has an associated source
        # for the error, keep only the first 2 digits after the decimal point
        localization_text = f"*Localization*:\n *-* Localization Type: Point\n *-* Coordinates: ra={data['ra']}, dec={data['dec']}, error radius={data['error']} deg"
        if data['error'] < SOURCE_RADIUS_THRESHOLD:
            localization_text += f"\n *-* Source Page Link: <{app_url}/source/{data['source_name']}|*{data['source_name']}*>"

    elif data['localization_name'] is not None:
        # the event has an associated skymap
        localization_text = f"*Localization*:\n *-* Localization Type: Skymap\n *-* Name: {data['localization_name']}"
    else:
        localization_text = (
            "*Localization*:\n *-* No localization available for this event (yet)"
        )

    external_links_text = None
    if len(data['links']):
        external_links_text = "*External Links*:"
        for key, value in data['links'].items():
            external_links_text += f"\n *-* <{value}|*{key}*>"

    tags_text = None
    if len(data['tags']) > 0:
        tags_text = f"*Event tags*: {','.join(data['tags'])}"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": time_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": notice_type_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": localization_text}},
    ]

    if external_links_text is not None:
        blocks.append({"type": "divider"})
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": external_links_text}}
        )
    if tags_text is not None:
        blocks.append({"type": "divider"})
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": tags_text}}
        )

    return blocks


def gcn_email_notification(target, data=None, new_tag=False):
    # Now, we will create an HTML email that describes the message we want to send by email

    if data['new_event']:
        header_text = f"<h3>New GCN Event: <a href='{app_url}{target['url']}'>{data['dateobs']}</a> ({data['notice_type']})</h3>"
        subject = f"{cfg['app.title']} - New GCN Event: {data['dateobs']} ({data['notice_type']})"
    elif new_tag:
        header_text = f"<h3>New tag added to Event: <a href='{app_url}{target['url']}'>{data['dateobs']}</a> ({data['notice_type']})</h3>"
        subject = f"{cfg['app.title']} - New tag added to Event: {data['dateobs']} ({data['notice_type']})"
    else:
        header_text = f"<h3>New notice for Event: <a href='{app_url}{target['url']}'>{data['dateobs']}</a> ({data['notice_type']})</h3>"
        subject = f"{cfg['app.title']} - New notice for Event: {data['dateobs']} ({data['notice_type']})"

    time_text = f"<div><h4>Time:</h4><ul><li>Trigger Time (T0): {data['dateobs']}</li><li>Time since T0: {data['time_since_dateobs']}</li></ul></div>"
    notice_type_text = f"<div><h4>Notice Type:</h4> {data['notice_type']}</div>"

    if data['ra'] is not None and data['dec'] is not None and data['error'] is not None:
        localization_text = f"<h4>Localization:</h4><ul><li>Localization Type: Point</li><li>Coordinates: ra={data['ra']}, dec={data['dec']}, error radius={data['error']} deg</li>"
        if data['error'] < SOURCE_RADIUS_THRESHOLD:
            localization_text += f"<li>Associated source Link: <a href='{app_url}/source/{data['source_name']}'>{data['source_name']}</a></li>"
    elif data['localization_name'] is not None:
        # the event has an associated skymap
        localization_text = f"<h4>Localization:</h4><ul><li>Localization Type: Skymap</li><li>Name: {data['localization_name']}</li>"
    else:
        localization_text = "<h4>Localization:</h4><ul><li>No localization available for this event (yet)</li>"

    localization_text = f"<div>{localization_text}</ul></div>"

    external_links_text = None
    if len(data['links']):
        external_links_text = "<h4>External Links:</h4><ul>"
        for key, value in data['links'].items():
            external_links_text += f"<li><a href='{value}'>{key}</a></li>"
        external_links_text += "</ul>"

    tags_text = None
    if len(data['tags']) > 0:
        tags_text = f"<h4>Event tags: {','.join(data['tags'])}</h4><ul>"

    return subject, "".join(
        [
            "<!DOCTYPE html><html><head><style>body {font-family: Arial, Helvetica, sans-serif;}</style></head>",
            "<body>",
            header_text,
            time_text,
            notice_type_text,
            localization_text,
            "</body></html>",
            external_links_text if external_links_text is not None else "",
            tags_text if tags_text is not None else "",
        ]
    )


def source_notification_content(target, target_type="classification"):
    # get the most recent classification for this source that has the same classification as the notification
    if target_type == "classification":
        data = {
            "source_name": target.obj_id,
            "ra": target.obj.ra,
            "dec": target.obj.dec,
            "redshift": target.obj.redshift,
            "classification_name": target.classification,
            "classification_probability": target.probability,
            "classification_date": Time(target.modified).isot,
        }
    elif target_type == "spectrum":
        data = {
            "source_name": target.obj_id,
            "ra": target.obj.ra,
            "dec": target.obj.dec,
            "redshift": target.obj.redshift,
            "spectrum_uploaded_by": target.owner.username,
            "spectrum_reduced_by": [user.username for user in target.reducers],
            "spectrum_observed_by": [user.username for user in target.observers],
            "spectrum_instrument": target.instrument.name,
        }
    else:
        raise ValueError(f"Unknown target type: {target_type}")

    if len(target.obj.photstats) > 0:
        first_detected_mjd = target.obj.photstats[0].first_detected_mjd
        first_detected = Time(first_detected_mjd, format="mjd").isot

        last_detected_mjd = target.obj.photstats[0].last_detected_mjd
        last_detected = Time(last_detected_mjd, format="mjd").isot
        nb_detections = target.obj.photstats[0].num_det_global

        data["first_detected"] = first_detected
        data["last_detected"] = last_detected
        data["nb_detections"] = nb_detections

    else:
        data["created_at"] = Time(target.obj.created_at).isot
        data["nb_detections"] = 0

    return data


def source_slack_notification(target, data=None):
    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

    # if data is None, raise an error
    if data is None:
        raise ValueError("No data provided for source notification")

    if 'classification_name' in data:
        header_text = f"New *{data['classification_name']}*: <{app_url}{target['url']}|*{data['source_name']}*>"

        classification_stats = f"*Classification Stats:*\n - Score/Probability: {data['classification_probability']:.2f} \n - Date: {data['classification_date']}"

        source_coordinates = (
            f"*Source Coordinates:*\n - RA: {data['ra']} \n - Dec: {data['dec']}"
        )
        # add the redshift if it exists
        if data['redshift'] is not None:
            source_coordinates += f"\n - Redshift: {data['redshift']}"

        if data['nb_detections'] > 0:
            source_detection_stats = f"*Source Detection Stats:*\n - First Detection: {data['first_detected']} \n - Last Detection: {data['last_detected']} \n - Number of Detections: {data['nb_detections']}"
        else:
            source_detection_stats = f"*Source Detection Stats:*\n - Source created at: {data['created_at']} \n - Not yet detected (no photometry)"

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header_text,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": classification_stats,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": source_coordinates,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": source_detection_stats,
                },
            },
        ]
    elif "spectrum_instrument" in data:
        header_text = (
            f"New Spectrum: <{app_url}{target['url']}|*{data['source_name']}*>"
        )

        spectrum_info = f"*Spectrum Info:*\n - Instrument: {data['spectrum_instrument']} \n - Uploaded by: {data['spectrum_uploaded_by']} \n - Reduced by: {', '.join(data['spectrum_reduced_by'])} \n - Observed by: {', '.join(data['spectrum_observed_by'])}"

        source_coordinates = (
            f"*Source Coordinates:*\n - RA: {data['ra']} \n - Dec: {data['dec']}"
        )
        # add the redshift if it exists
        if data['redshift'] is not None:
            source_coordinates += f"\n - Redshift: {data['redshift']}"

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header_text,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": spectrum_info,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": source_coordinates,
                },
            },
        ]


def source_email_notification(target, data=None):
    # Now, we will create an HTML email that describes the message we want to send by email

    if data is None:
        raise ValueError("No data provided for source notification")

    if 'classification_name' in data:
        header_text = f"<h3>New {data['classification_name']}: <a href='{app_url}{target['url']}'>{data['source_name']}</a></h3>"
        subject = f"{cfg['app.title']} - New {data['classification_name']}: {data['source_name']}"

        classification_stats = f"<div><h4>Classification Stats:</h4><ul><li>Score/Probability: {data['classification_probability']:.2f}</li><li>Date: {data['classification_date']}</li></ul></div>"

        source_coordinates = f"<div><h4>Source Coordinates:</h4><ul><li>RA: {data['ra']}</li><li>Dec: {data['dec']}</li>"
        # add the redshift if it exists
        if data['redshift'] is not None:
            source_coordinates += f"<li>Redshift: {data['redshift']}</li>"
        source_coordinates += "</ul></div>"
        if data['nb_detections'] > 0:
            source_detection_stats = f"<div><h4>Source Detection Stats:</h4><ul><li>First Detection: {data['first_detected']}</li><li>Last Detection: {data['last_detected']}</li><li>Number of Detections: {data['nb_detections']}</li></ul></div>"
        else:
            source_detection_stats = f"<div><h4>Source Detection Stats:</h4><ul><li>Source created at: {data['created_at']}</li><li>Not yet detected (no photometry)</li></ul></div>"

        return subject, (
            "<!DOCTYPE html><html><head><style>body {font-family: Arial, Helvetica, sans-serif;}</style></head>"
            + "<body>"
            + header_text
            + classification_stats
            + source_coordinates
            + source_detection_stats
            + "</body></html>"
        )
    elif "spectrum_instrument" in data:
        header_text = f"<h3>New Spectrum: <a href='{app_url}{target['url']}'>{data['source_name']}</a></h3>"
        subject = f"{cfg['app.title']} - New Spectrum: {data['source_name']}"

        spectrum_info = f"<div><h4>Spectrum Info:</h4><ul><li>Instrument: {data['spectrum_instrument']}</li><li>Uploaded by: {data['spectrum_uploaded_by']}</li><li>Reduced by: {', '.join(data['spectrum_reduced_by'])}</li><li>Observed by: {', '.join(data['spectrum_observed_by'])}</li></ul></div>"

        source_coordinates = f"<div><h4>Source Coordinates:</h4><ul><li>RA: {data['ra']}</li><li>Dec: {data['dec']}</li>"
        # add the redshift if it exists
        if data['redshift'] is not None:
            source_coordinates += f"<li>Redshift: {data['redshift']}</li>"
        source_coordinates += "</ul></div>"

        return subject, (
            "<!DOCTYPE html><html><head><style>body {font-family: Arial, Helvetica, sans-serif;}</style></head>"
            + "<body>"
            + header_text
            + spectrum_info
            + source_coordinates
            + "</body></html>"
        )


def post_notification(request_body, timeout=2):
    notifications_microservice_url = (
        f'http://127.0.0.1:{cfg["ports.notification_queue"]}'
    )

    resp = requests.post(
        notifications_microservice_url, json=request_body, timeout=timeout
    )
    if resp.status_code != 200:
        log(
            f'Notification request failed for {request_body["target_class_name"]} with ID {request_body["target_id"]}: {resp.content}'
        )
        return False
    else:
        return True
