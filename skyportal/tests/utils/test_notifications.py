import pytest

from skyportal.utils.notifications import (
    SOURCE_RADIUS_THRESHOLD,
    followup_request_email_notification,
    followup_request_slack_notification,
    gcn_email_notification,
    gcn_slack_notification,
    source_email_notification,
    source_slack_notification,
)


def _gcn_data(**overrides):
    data = {
        "new_event": True,
        "dateobs": "2024-01-01T00:00:00",
        "notice_type": "TEST_NOTICE",
        "time_since_dateobs": "1 hour",
        "ra": None,
        "dec": None,
        "error": None,
        "localization_name": "bayestar.fits.gz",
        "source_name": None,
        "links": {},
        "tags": [],
    }
    data.update(overrides)
    return data


def _section_texts(blocks):
    return [b["text"]["text"] for b in blocks if b["type"] == "section"]


def test_gcn_slack_header_variants():
    target = {"url": "/gcn_events/2024-01-01T00:00:00"}

    new_event = _section_texts(gcn_slack_notification(target, _gcn_data()))[0]
    assert new_event.startswith("New Event:")
    assert "2024-01-01T00:00:00" in new_event
    assert "TEST_NOTICE" in new_event

    tagged = _section_texts(
        gcn_slack_notification(target, _gcn_data(new_event=False), new_tag=True)
    )[0]
    assert tagged.startswith("New tag added to Event:")

    notice = _section_texts(
        gcn_slack_notification(target, _gcn_data(new_event=False), new_tag=False)
    )[0]
    assert notice.startswith("New notice for Event:")


def test_gcn_slack_skymap_localization():
    target = {"url": "/gcn_events/x"}
    texts = "\n".join(_section_texts(gcn_slack_notification(target, _gcn_data())))
    assert "Localization Type: Skymap" in texts
    assert "bayestar.fits.gz" in texts


def test_gcn_slack_point_localization_links_to_source():
    target = {"url": "/gcn_events/x"}
    data = _gcn_data(
        ra=12.3,
        dec=-45.6,
        error=SOURCE_RADIUS_THRESHOLD / 2,  # within threshold -> include source link
        source_name="ZTF24abcdefg",
        localization_name=None,
    )
    texts = "\n".join(_section_texts(gcn_slack_notification(target, data)))
    assert "Localization Type: Point" in texts
    assert "ra=12.3, dec=-45.6" in texts
    assert "ZTF24abcdefg" in texts  # source page link added

    # outside the threshold -> no source link
    data["error"] = SOURCE_RADIUS_THRESHOLD * 2
    texts = "\n".join(_section_texts(gcn_slack_notification(target, data)))
    assert "Localization Type: Point" in texts
    assert "ZTF24abcdefg" not in texts


def test_gcn_slack_no_localization_with_links_and_tags():
    target = {"url": "/gcn_events/x"}
    data = _gcn_data(
        localization_name=None,
        links={"GraceDB": "https://gracedb.example/S1"},
        tags=["GW", "BNS"],
    )
    blocks = gcn_slack_notification(target, data)
    texts = "\n".join(_section_texts(blocks))
    assert "No localization available" in texts
    assert "External Links" in texts and "GraceDB" in texts
    assert "Event tags" in texts and "GW,BNS" in texts


def test_gcn_email_subject_and_body():
    target = {"url": "/gcn_events/2024-01-01T00:00:00"}
    subject, html = gcn_email_notification(target, _gcn_data())

    assert "New GCN Event: 2024-01-01T00:00:00 (TEST_NOTICE)" in subject
    assert html.startswith("<!DOCTYPE html>")
    assert "<h3>New GCN Event:" in html
    assert "Localization Type: Skymap" in html
    assert "bayestar.fits.gz" in html
    assert "Time since T0: 1 hour" in html


def _classification_data(**overrides):
    data = {
        "classification_name": "SN Ia",
        "source_name": "ZTF24abcdefg",
        "classification_probability": 0.95,
        "classification_date": "2024-01-01T00:00:00",
        "ra": 12.3,
        "dec": -45.6,
        "redshift": 0.1,
        "nb_detections": 3,
        "first_detected": "2024-01-01",
        "last_detected": "2024-01-03",
        "created_at": "2024-01-01",
    }
    data.update(overrides)
    return data


def _spectrum_data(**overrides):
    data = {
        "spectrum_instrument": "DBSP",
        "spectrum_uploaded_by": "alice",
        "spectrum_reduced_by": ["bob"],
        "spectrum_observed_by": ["carol", "dave"],
        "source_name": "ZTF24abcdefg",
        "ra": 12.3,
        "dec": -45.6,
        "redshift": 0.1,
    }
    data.update(overrides)
    return data


def test_source_slack_classification():
    target = {"url": "/source/ZTF24abcdefg"}
    texts = "\n".join(
        _section_texts(source_slack_notification(target, _classification_data()))
    )
    assert texts.startswith("New *SN Ia*:")
    assert "ZTF24abcdefg" in texts
    assert "Score/Probability: 0.95" in texts  # formatted to 2 d.p.
    assert "RA: 12.3" in texts and "Dec: -45.6" in texts and "Redshift: 0.1" in texts
    assert "First Detection: 2024-01-01" in texts
    assert "Number of Detections: 3" in texts


def test_source_slack_classification_without_detections():
    target = {"url": "/source/ZTF24abcdefg"}
    texts = "\n".join(
        _section_texts(
            source_slack_notification(target, _classification_data(nb_detections=0))
        )
    )
    assert "Not yet detected" in texts
    assert "Source created at: 2024-01-01" in texts


def test_source_slack_spectrum():
    target = {"url": "/source/ZTF24abcdefg"}
    texts = "\n".join(
        _section_texts(source_slack_notification(target, _spectrum_data()))
    )
    assert texts.startswith("New Spectrum:")
    assert "Instrument: DBSP" in texts
    assert "Reduced by: bob" in texts
    assert "Observed by: carol, dave" in texts


def test_source_email_classification():
    target = {"url": "/source/ZTF24abcdefg"}
    subject, html = source_email_notification(target, _classification_data())
    assert "New SN Ia: ZTF24abcdefg" in subject
    assert html.startswith("<!DOCTYPE html>")
    assert "<h3>New SN Ia:" in html
    assert "Score/Probability: 0.95" in html
    assert "Number of Detections: 3" in html


def test_source_email_spectrum():
    target = {"url": "/source/ZTF24abcdefg"}
    subject, html = source_email_notification(target, _spectrum_data())
    assert "New Spectrum: ZTF24abcdefg" in subject
    assert "Instrument: DBSP" in html
    assert "Observed by: carol, dave" in html


def test_source_notifications_require_data():
    with pytest.raises(ValueError, match="No data provided"):
        source_slack_notification({"url": "/source/x"}, None)
    with pytest.raises(ValueError, match="No data provided"):
        source_email_notification({"url": "/source/x"}, None)


def _followup_data():
    return {
        "obj": {
            "id": "ZTF24abcdefg",
            "ra_hms": "01:23:45.6",
            "dec_dms": "-12:34:56.7",
            "ra": 20.94,
            "dec": -12.582,
            "l": 100.123456,
            "b": -45.654321,
            "thumbnails": [],
        },
        "request": {
            "new": True,
            "allocation": "ZTF Partnership",
            "group": "GROWTH",
            "user": "alice@example.com",
            "time": "2024-01-01T00:00:00",
            "payload": {"observation_type": "imaging", "exposure_time": 300},
        },
    }


def test_followup_request_slack_new_updated_and_payload():
    data = _followup_data()
    blocks = followup_request_slack_notification(data)
    texts = "\n".join(_section_texts(blocks))

    assert "New Follow-up request:" in texts
    assert "ZTF24abcdefg" in texts
    assert "ZTF Partnership" in texts and "GROWTH" in texts
    # payload keys are title-cased: "observation_type" -> "Observation_type"
    assert "Observation_type" in texts and "imaging" in texts
    assert "Exposure_time" in texts

    # the final block is the action buttons (not a section)
    buttons = blocks[-1]
    assert buttons["type"] == "actions"
    labels = [el["text"]["text"] for el in buttons["elements"]]
    assert labels == ["Observability", "Finding Chart", "SDSS", "LS DR10", "TNS"]

    data["request"]["new"] = False
    texts = "\n".join(_section_texts(followup_request_slack_notification(data)))
    assert "Updated Follow-up request:" in texts


def test_followup_request_slack_comments():
    data = _followup_data()
    data["comments"] = ["looks promising", "schedule asap"]
    texts = "\n".join(_section_texts(followup_request_slack_notification(data)))
    assert "Comments" in texts and "looks promising" in texts

    data["comments"] = []
    texts = "\n".join(_section_texts(followup_request_slack_notification(data)))
    assert "No comments yet" in texts


def test_followup_request_email():
    data = _followup_data()
    subject, html = followup_request_email_notification(data)

    assert "New Follow-up Request: ZTF24abcdefg" in subject
    assert html.startswith("<!DOCTYPE html>")
    assert "<h3>New Follow-up Request:" in html
    assert "α, δ = 20.940000, -12.582000" in html  # formatted to 6 d.p.
    assert "Allocation: ZTF Partnership" in html
    assert "observation_type: imaging" in html  # email keeps the raw payload key
    assert "Observability" in html and "TNS" in html  # buttons

    data["request"]["new"] = False
    subject, html = followup_request_email_notification(data)
    assert "Updated Follow-up Request: ZTF24abcdefg" in subject
    assert "<h3>Updated Follow-up Request:" in html
