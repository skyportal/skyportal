from skyportal.models import (
    GcnEvent,
    Obj,
)
from astropy.time import Time

from skyportal.models.gcn import SOURCE_RADIUS_THRESHOLD

import sqlalchemy as sa
import datetime
import lxml


def gcn_slack_notification(session, target, app_url):
    # the target is a UserNotification. It contains a text, and an url
    # the url contains the dateobs
    # the text contains either "New notice for GCN Event" or "New GCN Event", telling us if it's a new event or a new notice for an existing event

    # get the event dateobs
    dateobs = target.url.split("gcn_events/")[-1].split("/")[0]
    dateobs_txt = Time(dateobs).isot
    source_name = dateobs_txt.replace(":", "-")
    notice_type = target.text.split(" Notice Type *")[-1].split("*")[0]
    new_event = True if "New GCN Event" in target.text else False

    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

    stmt = sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
    gcn_event = session.execute(stmt).scalars().first()

    tags = gcn_event.tags

    if 'GRB' in tags:
        # we want the name to be like GRB YYMMDD.HHMM
        display_source_name = f"GRB{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
    elif 'GW' in tags:
        display_source_name = f"GW{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}.{dateobs_txt[11:13]}{dateobs_txt[14:16]}{dateobs_txt[17:19]}"
    else:
        display_source_name = source_name

    # get the most recent notice for this event
    last_gcn_notice = gcn_event.gcn_notices[-1]

    if new_event:
        header_text = (
            f"New Event: <{app_url}{target.url}|*{dateobs_txt}*> ({notice_type})"
        )
    else:
        header_text = f"New notice for Event: <{app_url}{target.url}|*{dateobs_txt}*> ({notice_type})"

    time_since_dateobs = datetime.datetime.utcnow() - gcn_event.dateobs
    # remove the microseconds from the timedelta
    time_since_dateobs = time_since_dateobs - datetime.timedelta(
        microseconds=time_since_dateobs.microseconds
    )
    time_text = f"*Time*:\n *-* Trigger Time (T0): {dateobs}\n *-* Time since T0: {time_since_dateobs}"
    notice_type_text = f"*Notice Type*: {notice_type}"

    # now we figure out if the localization is a skymap or a point source

    notice_content = lxml.etree.fromstring(last_gcn_notice.content)

    loc = notice_content.find('./WhereWhen/ObsDataLocation/ObservationLocation')
    ra = loc.find('./AstroCoords/Position2D/Value2/C1')
    dec = loc.find('./AstroCoords/Position2D/Value2/C2')
    error = loc.find('./AstroCoords/Position2D/Error2Radius')

    if ra is not None and dec is not None and error is not None:
        # the event has an associated source
        ra = float(ra.text)
        dec = float(dec.text)
        error = float(error.text)
        # for the error, keep only the first 2 digits after the decimal point
        error = float(f"{error:.2f}")
        localization_text = f"*Localization*:\n *-* Localization Type: Point\n *-* Coordinates: ra={ra}, dec={dec}, error radius={error} deg"
        if error < SOURCE_RADIUS_THRESHOLD:
            localization_text += f"\n *-* Source Link: <{app_url}/source/{display_source_name}|*{display_source_name}*>"

    else:
        # the event has an associated skymap
        localization_text = f"*Localization*:\n *-* Localization Type: Skymap\n *-* Link: <{app_url}{target.url}|*{gcn_event.dateobs}*>"

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


def source_slack_notification(session, target, app_url):
    # the target is a UserNotification. It contains a text, and an url
    # the text contains the source name, and the classification
    # the text looks like: New classification *{target.classification}* for source *{target.obj_id}*

    # get the source name
    source_name = target.text.split(" for source *")[-1].split("*")[0]

    # get the classification
    classification_name = target.text.split("classification *")[-1].split("*")[0]

    # Now, we query the obj/source table to get the source coordinates, and classifications history
    stmt = sa.select(Obj).where(Obj.id == source_name)
    source = session.execute(stmt).scalars().first()

    # get the most recent classification for this source that has the same classification as the notification

    classification = None
    for c in source.classifications:
        if c.classification == classification_name and classification is None:
            classification = c
        elif (
            c.classification == classification_name
            and c.modified > classification.modified
        ):
            classification = c

    print(source.photstats[0])

    first_detected_mjd = source.photstats[0].first_detected_mjd
    first_detected = Time(first_detected_mjd, format="mjd").isot

    last_detected_mjd = source.photstats[0].last_detected_mjd
    last_detected = Time(last_detected_mjd, format="mjd").isot

    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

    header_text = f"New *{classification.classification}*: <{app_url}{target.url}|*{source_name}*>"

    classification_stats = f"*Classification Stats:*\n - Score/Probability: {classification.probability:.2f} \n - Date: {classification.modified}"

    source_coordinates = (
        f"*Source Coordinates:*\n - RA: {source.ra} \n - Dec: {source.dec}"
    )
    # add the redshift if it exists
    if source.redshift is not None:
        source_coordinates += f"\n - Redshift: {source.redshift}"

    source_detection_stats = f"*Source Detection Stats:*\n - First Detection: {first_detected} \n - Last Detection: {last_detected} \n - Number of Detections: {source.photstats[0].num_det_global}"

    source_link = f"Source Link: <{app_url}/source/{source_name}|*{source_name}*>"

    blocks = [
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
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": source_link,
            },
        },
    ]

    return blocks
