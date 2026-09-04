"""Which extractions notify, and which get tagged.

The two decisions with judgement in them are pure, so they are tested directly
against the extraction shape Circex writes.
"""

from skyportal.utils.gcn_extraction_tags import (
    classification_of,
    subtype_of,
    tag_name_for,
    wants_classification,
)

XRF = {"classification": {"classification": "X-ray Flash", "probability": 1.0}}


def test_classification_read_from_the_extraction():
    assert classification_of(XRF) == "X-ray Flash"


def test_extraction_without_a_classification():
    # A circular that reports only photometry classifies nothing.
    assert classification_of({"classification": None}) is None
    assert classification_of({}) is None
    assert classification_of(None) is None


def test_empty_watch_list_means_every_classification():
    assert wants_classification({"gcn_extractions": {}}, "X-ray Flash")
    assert wants_classification({"gcn_extractions": {"classifications": []}}, "Ia")
    assert wants_classification({}, "Ia")


def test_watch_list_selects_one_class():
    prefs = {"gcn_extractions": {"classifications": ["X-ray Flash"]}}
    assert wants_classification(prefs, "X-ray Flash")
    assert not wants_classification(prefs, "Ia")


def test_no_classification_never_notifies():
    # Without a class there is nothing to match, even on an empty watch list.
    assert not wants_classification({"gcn_extractions": {}}, None)
    assert not wants_classification({"gcn_extractions": {}}, "")


def test_unmapped_class_tags_nothing():
    assert tag_name_for("Ia") is None
    assert tag_name_for(None) is None


def test_configured_class_maps_to_its_tag():
    assert tag_name_for("X-ray Flash") == "XRFcandidate"


def test_subtype_read_from_the_extraction():
    """An X-ray flash is a GRB the taxonomy has no node for, so it is a subtype."""
    grb_xrf = {"classification": {"classification": "GRB", "subtype": "XRF candidate"}}
    assert subtype_of(grb_xrf) == "XRF candidate"
    assert classification_of(grb_xrf) == "GRB"


def test_extraction_without_a_subtype():
    assert subtype_of({"classification": {"classification": "GRB"}}) is None
    assert subtype_of({"classification": None}) is None
    assert subtype_of(None) is None
