from skyportal.app_utils import get_app_base_url

from skyportal.models import (
    GcnEvent,
)
from astropy.time import Time

from skyportal.models.gcn import SOURCE_RADIUS_THRESHOLD

import sqlalchemy as sa
import datetime
import lxml

from baselayer.app.env import load_env

env, cfg = load_env()

app_url = get_app_base_url()


def gcn_notification_content(target, session):
    dateobs = target.dateobs
    dateobs_txt = Time(dateobs).isot
    source_name = dateobs_txt.replace(":", "-")

    stmt = sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
    gcn_event = session.execute(stmt).scalars().first()

    tags = target.tags

    time_since_dateobs = datetime.datetime.utcnow() - gcn_event.dateobs
    # remove the microseconds from the timedelta
    time_since_dateobs = time_since_dateobs - datetime.timedelta(
        microseconds=time_since_dateobs.microseconds
    )

    new_event = False
    if gcn_event.gcn_notices is None or len(gcn_event.gcn_notices) < 2:
        new_event = True

    # get the most recent notice for this event
    if gcn_event.gcn_notices is not None and len(gcn_event.gcn_notices) > 0:
        last_gcn_notice = gcn_event.gcn_notices[-1]
        notice_type = last_gcn_notice.notice_type
        notice_content = lxml.etree.fromstring(last_gcn_notice.content)
        name = notice_content.find('./Why/Inference/Name')
    else:
        notice_type = 'No notice type'
        notice_content = None
        name = None

    if name is not None:
        source_name = (name.text).replace(" ", "")
    elif 'GRB' in tags:
        # we want the name to be like GRB YYMMDD.HHMM
        source_name = f"GRB{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
    elif 'GW' in tags:
        source_name = f"GW{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"

    if notice_content is not None:
        loc = notice_content.find('./WhereWhen/ObsDataLocation/ObservationLocation')
        ra = loc.find('./AstroCoords/Position2D/Value2/C1')
        dec = loc.find('./AstroCoords/Position2D/Value2/C2')
        error = loc.find('./AstroCoords/Position2D/Error2Radius')
    else:
        ra = None
        dec = None
        error = None

    if ra is not None:
        ra = float(ra.text)

    if dec is not None:
        dec = float(dec.text)

    if error is not None:
        error = float(error.text)

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
        'app_url': app_url,
    }


def gcn_slack_notification(target, data=None):

    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

    if data['new_event']:
        header_text = f"New Event: <{app_url}{target['url']}|*{data['dateobs']}*> ({data['notice_type']})"
    else:
        header_text = f"New notice for Event: <{app_url}{target['url']}|*{data['dateobs']}*> ({data['notice_type']})"

    time_text = f"*Time*:\n *-* Trigger Time (T0): {data['dateobs']}\n *-* Time since T0: {data['time_since_dateobs']}"
    notice_type_text = f"*Notice Type*: {data['notice_type']}"

    if data['ra'] is not None and data['dec'] is not None and data['error'] is not None:
        # the event has an associated source
        # for the error, keep only the first 2 digits after the decimal point
        localization_text = f"*Localization*:\n *-* Localization Type: Point\n *-* Coordinates: ra={data['ra']}, dec={data['dec']}, error radius={data['error']} deg"
        if data['error'] < SOURCE_RADIUS_THRESHOLD:
            localization_text += f"\n *-* Source Link: <{app_url}/source/{data['source_name']}|*{data['source_name']}*>"

    else:
        # the event has an associated skymap
        localization_text = f"*Localization*:\n *-* Localization Type: Skymap\n *-* Link: <{app_url}{target['url']}|*{data['dateobs']}*>"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": time_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": notice_type_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": localization_text}},
    ]

    return blocks


def gcn_email_notification(target, data=None):

    # Now, we will create an HTML email that describes the message we want to send by email

    if data['new_event']:
        header_text = f"<h3>New GCN Event: <a href='{app_url}{target['url']}'>{data['dateobs']}</a> ({data['notice_type']})</h3>"
        subject = f"{cfg['app.title']} - New GCN Event: {data['dateobs']} ({data['notice_type']})"
    else:
        header_text = f"<h3>New notice for Event: <a href='{app_url}{target['url']}'>{data['dateobs']}</a> ({data['notice_type']})</h3>"
        subject = f"{cfg['app.title']} - New notice for Event: {data['dateobs']} ({data['notice_type']})"

    time_text = f"<div><h4>Time:</h4><ul><li>Trigger Time (T0): {data['dateobs']}</li><li>Time since T0: {data['time_since_dateobs']}</li></ul></div>"
    notice_type_text = f"<div><h4>Notice Type:</h4> {data['notice_type']}</div>"

    if data['ra'] is not None and data['dec'] is not None and data['error'] is not None:
        localization_text = f"<h4>Localization:</h4><ul><li>Localization Type: Point</li><li>Coordinates: ra={data['ra']}, dec={data['dec']}, error radius={data['error']} deg</li>"
        if data['error'] < SOURCE_RADIUS_THRESHOLD:
            localization_text += f"<li>Associated source Link: <a href='{app_url}/source/{data['source_name']}'>{data['source_name']}</a></li>"
    else:
        # the event has an associated skymap
        localization_text = f"<h4>Localization:</h4><ul><li>Localization Type: Skymap</li><li>Link: <a href='{app_url}{target['url']}'>{data['dateobs']}</a><li>"

    localization_text = f"<div>{localization_text}</ul></div>"

    return subject, (
        "<!DOCTYPE html><html><head><style>body {font-family: Arial, Helvetica, sans-serif;}</style></head>"
        + "<body>"
        + header_text
        + time_text
        + notice_type_text
        + localization_text
        + "</body></html>"
    )


def source_notification_content(classification):

    # get the most recent classification for this source that has the same classification as the notification

    data = {
        "source_name": classification.obj_id,
        "ra": classification.obj.ra,
        "dec": classification.obj.dec,
        "redshift": classification.obj.redshift,
        "classification_name": classification.classification,
        "classification_probability": classification.probability,
        "classification_date": Time(classification.modified).isot,
    }

    if len(classification.obj.photstats) > 0:
        first_detected_mjd = classification.obj.photstats[0].first_detected_mjd
        first_detected = Time(first_detected_mjd, format="mjd").isot

        last_detected_mjd = classification.obj.photstats[0].last_detected_mjd
        last_detected = Time(last_detected_mjd, format="mjd").isot
        nb_detections = classification.obj.photstats[0].num_det_global

        data["first_detected"] = first_detected
        data["last_detected"] = last_detected
        data["nb_detections"] = nb_detections

    else:
        data["created_at"] = Time(classification.obj.created_at).isot
        data["nb_detections"] = 0

    return data


def source_slack_notification(target, data=None):

    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

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


def source_email_notification(target, data=None):
    # Now, we will create an HTML email that describes the message we want to send by email

    header_text = f"<h3>New {data['classification_name']}: <a href='{app_url}{target['url']}'>{data['source_name']}</a></h3>"
    subject = (
        f"{cfg['app.title']} - New {data['classification_name']}: {data['source_name']}"
    )

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
