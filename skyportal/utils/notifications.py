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
from skyportal.utils.calculations import deg2hms, deg2dms, radec2lb
from skyportal.email_utils import send_email

env, cfg = load_env()

app_url = get_app_base_url()

ALERT_THUMB_TYPES = ["new", "ref", "sub"]
ARCHIVE_THUMB_TYPES = ["sdss", "ls", "ps1"]
ALLOWED_THUMBNAIL_TYPES = [
    *ALERT_THUMB_TYPES,
    *ARCHIVE_THUMB_TYPES,
]

SLACK_DIVIDER = {"type": "divider"}

SLACK_BASE_URL = cfg['slack.expected_url_preamble']
if SLACK_BASE_URL.endswith('/'):
    SLACK_URL = SLACK_BASE_URL[:-1]

SLACK_URL = f"{SLACK_URL}/services"

SLACK_MICROSERVICE_URL = f'http://127.0.0.1:{cfg["slack.microservice_port"]}'

email_enabled = False
if cfg.get("email_service") == "sendgrid" or cfg.get("email_service") == "smtp":
    email_enabled = True

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
    try:
        resp = requests.post(
            notifications_microservice_url, json=request_body, timeout=timeout
        )
    except requests.exceptions.ReadTimeout:
        log(
            f'Notification request timed out for {request_body["target_class_name"]} with ID {request_body["target_id"]}'
        )
        return False
    except Exception as e:
        log(
            f'Notification request failed for {request_body["target_class_name"]} with ID {request_body["target_id"]}: {e}'
        )
        return False

    if resp.status_code != 200:
        log(
            f'Notification request failed for {request_body["target_class_name"]} with ID {request_body["target_id"]}: {resp.content}'
        )
        return False
    else:
        return True


def followup_request_notification_content(target, session):
    include_comments = False
    if target.allocation.altdata.get("include_comments", False) in [
        True,
        "T",
        "True",
        "true",
        "t",
        1,
        "1",
    ]:
        include_comments = True

    target_name = target.obj.id
    ra, dec = target.obj.ra, target.obj.dec
    ra_hms, ra_dms = deg2hms(ra), deg2dms(dec)
    if not ra_dms.startswith("-"):
        ra_dms = "+" + ra_dms
    l, b = radec2lb(ra, dec)

    allocation = (
        str(target.allocation.instrument.telescope.nickname)
        + "/"
        + str(target.allocation.instrument.name)
        + " ("
        + str(target.allocation.pi)
        + ")"
    )
    group = target.allocation.group.name
    user = (
        target.requester.username
        if (
            target.requester.first_name in ["", None]
            or target.requester.last_name in ["", None]
        )
        else f"{target.requester.first_name} {target.requester.last_name}"
    ) + (
        f" ({str(target.requester.affiliations[0]).strip()})"
        if (
            isinstance(target.requester.affiliations, list)
            and len(target.requester.affiliations) > 0
        )
        else ""
    )
    time = str(Time(target.created_at).isot).split(".")[0] + " UTC"

    # then we want information about the payload itself
    payload = target.payload

    # we want to loop over the payload, to build a dict like:
    # key: value as a string
    payload = {key: str(value) for key, value in payload.items()}

    # check if its a new request, or a request that has been updated
    # we don't have an easy way to check this since these entries are edited right after they are submitted to the database
    # so instead we'll define "new" requests where the last_updated is within 1 minute of the created_at
    new_request = False
    if (target.modified - target.created_at).seconds < 60:
        new_request = True

    # last but not least, we want to look for thumbnails
    # if we find all 3 "alert" types: new, ref, sub, we return these 3
    # otherwise we return sdss, ls, and ps1 in that order
    thumbnails = [t for t in target.obj.thumbnails if t.type in ALLOWED_THUMBNAIL_TYPES]
    # we may have more than one thumbnail of the same type, so we want to de-duplicate
    # deduplicate by type, keeping the latest one (create_at) for each type
    # sort by date, most recent first
    thumbnails = sorted(thumbnails, key=lambda t: t.created_at, reverse=True)
    thumbnails_by_type = {t: None for t in ALLOWED_THUMBNAIL_TYPES}
    for thumbnail in thumbnails:
        if thumbnails_by_type[thumbnail.type] is None:
            thumbnails_by_type[thumbnail.type] = thumbnail

    # now we check if we have all the alert types
    # if we do, keep those
    # otherwise, keep the archive types
    if all(thumbnails_by_type[t] is not None for t in ALERT_THUMB_TYPES):
        thumbnails = [thumbnails_by_type[t] for t in ALERT_THUMB_TYPES]
    else:
        thumbnails = [
            thumbnails_by_type[t]
            for t in ARCHIVE_THUMB_TYPES
            if thumbnails_by_type.get(t, None) is not None
        ]

    # make them simple dicts
    thumbnails = [
        {
            "url": app_url + t.public_url
            if t.type in ALERT_THUMB_TYPES
            else t.public_url,
            "type": t.type,
        }
        for t in thumbnails
    ]

    data = {
        "obj": {
            "id": target_name,
            "ra": ra,
            "dec": dec,
            "ra_hms": ra_hms,
            "dec_dms": ra_dms,
            "l": l,
            "b": b,
            "thumbnails": thumbnails,
        },
        "request": {
            "allocation": allocation,
            "group": group,
            "user": user,
            "time": time,
            "payload": payload,
            "new": new_request,
        },
    }

    if include_comments:
        comments = []
        for comment in target.obj.comments:
            comments.append(
                (
                    f"{comment.author.username} ({str(comment.created_at).split('.')[0]}): {comment.text}",
                    comment.created_at,
                )
            )

        # sort by date, most recent first, then remove the date
        comments = sorted(comments, key=lambda c: c[1], reverse=True)
        data["comments"] = [c[0] for c in comments]

    return data


def followup_request_slack_notification(data):
    header_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f'*<{app_url}/source/{data["obj"]["id"]}|{data["obj"]["id"]}>*\n*{data["obj"]["ra_hms"]} {data["obj"]["dec_dms"]}*\n*'
            + f'α, δ* = {data["obj"]["ra"]:0.6f}, {data["obj"]["dec"]:0.6f}\n'
            + f'*l, b* = {data["obj"]["l"]:0.6f}, {data["obj"]["b"]:0.6f}',
        },
    }
    if len(data["obj"]["thumbnails"]) > 0:
        header_section["accessory"] = {
            "type": "image",
            "image_url": data["obj"]["thumbnails"][0]["url"],
            "alt_text": data["obj"]["thumbnails"][0]["type"],
        }

    request_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f'*{"New" if data["request"]["new"] else "Updated"} Follow-up request:*\n'
            + f'\t• *Allocation*:  {data["request"]["allocation"]}\n'
            + f'\t• *Group*:  {data["request"]["group"]}\n'
            + f'\t• *User:*  {data["request"]["user"]}\n'
            + f'\t• *Time:*  {data["request"]["time"]}',
        },
    }
    if len(data["obj"]["thumbnails"]) > 1:
        request_section["accessory"] = {
            "type": "image",
            "image_url": data["obj"]["thumbnails"][1]["url"],
            "alt_text": data["obj"]["thumbnails"][1]["type"],
        }

    payload_section = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Payload:*\n"},
    }

    for key, value in data["request"]["payload"].items():
        payload_section["text"][
            "text"
        ] += f'\t• *{str(key).lower().capitalize()}*: {value}\n'

    if len(data["obj"]["thumbnails"]) > 2:
        payload_section["accessory"] = {
            "type": "image",
            "image_url": data["obj"]["thumbnails"][2]["url"],
            "alt_text": data["obj"]["thumbnails"][2]["type"],
        }

    buttons = {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "emoji": True, "text": "Observability"},
                "style": "primary",
                "url": f"{app_url}/observability/{data['obj']['id']}",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "emoji": True, "text": "Finding Chart"},
                "style": "primary",
                "url": f"{app_url}/source/{data['obj']['id']}/finder",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "emoji": True, "text": "SDSS"},
                "url": f"https://skyserver.sdss.org/dr18/VisualTools/navi?opt=G&ra={data['obj']['ra']}&dec={data['obj']['dec']}&scale=0.1",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "emoji": True, "text": "LS DR9"},
                "url": f"https://www.legacysurvey.org/viewer?ra={data['obj']['ra']}&dec={data['obj']['dec']}&layer=ls-dr9&photoz-dr9&zoom=16&mark={data['obj']['ra']},{data['obj']['dec']}",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "emoji": True, "text": "TNS"},
                "url": f"https://www.wis-tns.org/search?&ra={data['obj']['ra']}&decl={data['obj']['dec']}&radius=5&coords_unit=arcsec",
            },
        ],
    }

    blocks = [
        SLACK_DIVIDER,
        header_section,
        SLACK_DIVIDER,
        request_section,
        SLACK_DIVIDER,
        payload_section,
    ]

    if "comments" in data:
        if len(data["comments"]) > 0:
            comments_section = {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Comments:*\n"},
            }
            for comment in data["comments"]:
                comments_section["text"]["text"] += f'\t• {comment}\n'
            blocks.append(comments_section)
        else:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Comments:*\nNo comments yet"},
                }
            )

    return blocks + [buttons]


def followup_request_email_notification(data):
    header_text = f"<h3>{'New' if data['request']['new'] else 'Updated'} Follow-up Request: <a href='{app_url}/source/{data['obj']['id']}'>{data['obj']['id']}</a></h3>"
    subject = f"{cfg['app.title']} - {'New' if data['request']['new'] else 'Updated'} Follow-up Request: {data['obj']['id']}"

    obj_section = (
        "<div>"
        f"<p><b>{data['obj']['ra_hms']} {data['obj']['dec_dms']}</b></p>"
        f"<p>α, δ = {data['obj']['ra']:0.6f}, {data['obj']['dec']:0.6f}</p>"
        f"<p>l, b = {data['obj']['l']:0.6f}, {data['obj']['b']:0.6f}</p>"
        "</div>"
    )

    if len(data['obj']['thumbnails']) > 0:
        # make one row with all the thumbnails
        thumbnails_section = "<div style='display: flex; flex-wrap: wrap;'>"
        for thumbnail in data['obj']['thumbnails']:
            thumbnails_section += f"<img src='{thumbnail['url']}' style='max-width: 100%; max-height: 100%; margin: 5px;' title='{thumbnail['type']}' />"
        thumbnails_section += "</div>"
    else:
        thumbnails_section = ""

    request_section = (
        "<div><h4>Request:</h4><ul>"
        f"<li>Allocation: {data['request']['allocation']}</li>"
        f"<li>Group: {data['request']['group']}</li>"
        f"<li>User: {data['request']['user']}</li>"
        f"<li>Time: {data['request']['time']}</li>"
        "</ul></div>"
    )

    payload_section = "<div><h4>Payload:</h4><ul>"
    for key, value in data["request"]["payload"].items():
        payload_section += f"<li>{key}: {value}</li>"
    payload_section += "</ul></div>"

    comments_section = ""
    if "comments" in data:
        if len(data["comments"]) > 0:
            comments_section = "<div><h4>Comments:</h4><ul>"
            for comment in data["comments"]:
                comments_section += f"<li>{comment}</li>"

            comments_section += "</ul></div>"
        else:
            comments_section = (
                "<div><h4>Comments:</h4><ul><li>No comments yet</li></ul></div>"
            )

    buttons = (
        "<div style='display: flex; gap: 8px;'>"
        f"<a href='{app_url}/observability/{data['obj']['id']}'><button>Observability</button></a>"
        f"<a href='{app_url}/source/{data['obj']['id']}/finder'><button>Finding Chart</button></a>"
        f"<a href='https://skyserver.sdss.org/dr18/VisualTools/navi?opt=G&ra={data['obj']['ra']}&dec={data['obj']['dec']}&scale=0.1'><button>SDSS</button></a>"
        f"<a href='https://www.legacysurvey.org/viewer?ra={data['obj']['ra']}&dec={data['obj']['dec']}&layer=ls-dr9&photoz-dr9&zoom=16&mark={data['obj']['ra']},{data['obj']['dec']}'><button>LS DR9</button></a>"
        f"<a href='https://www.wis-tns.org/search?&ra={data['obj']['ra']}&decl={data['obj']['dec']}&radius=5&coords_unit=arcsec'><button>TNS</button></a>"
        "</div>"
    )

    return subject, (
        "<!DOCTYPE html><html><head><style>body {font-family: Arial, Helvetica, sans-serif;}</style></head>"
        + "<body>"
        + header_text
        + obj_section
        + thumbnails_section
        + request_section
        + payload_section
        + comments_section
        + buttons
        + "</body></html>"
    )


def request_notify_by_slack(request, session, is_update=None):
    altdata = request.allocation.altdata

    if not isinstance(altdata, dict):
        raise ValueError('No altdata found in allocation.')

    if not all(
        key in altdata for key in ['slack_workspace', 'slack_channel', 'slack_token']
    ):
        raise ValueError('Missing required keys in allocation altdata.')

    content = followup_request_notification_content(request, session)
    if is_update is not None:  # if we have an explicit is_update, use that
        content['request']['new'] = not is_update
    blocks = followup_request_slack_notification(content)

    data = json.dumps(
        {
            "url": f"{SLACK_URL}/{altdata['slack_workspace']}/{altdata['slack_channel']}/{altdata['slack_token']}",
            "text": "test",
            "blocks": blocks,
        }
    )

    r = requests.post(
        SLACK_MICROSERVICE_URL,
        data=data,
        headers={'Content-Type': 'application/json'},
    )
    r.raise_for_status()


def request_notify_by_email(request, session, is_update=None):
    # if not email_enabled:
    #     raise RuntimeError('Email notifications are not enabled.')

    altdata = request.allocation.altdata

    if not isinstance(altdata, dict):
        raise ValueError('No altdata found in allocation.')

    if 'email' not in altdata:
        raise ValueError('Missing required key in allocation altdata.')

    content = followup_request_notification_content(request, session)
    if is_update is not None:  # if we have an explicit is_update, use that
        content['request']['new'] = not is_update
    subject, body = followup_request_email_notification(content)

    send_email(
        recipients=altdata['email'].split(","),
        subject=subject,
        body=body,
    )
