"""Which identifier each broker route takes.

Three of the object routes were once spelled /alerts/{id} with the id typed as
a candid, so these pin the segment each one actually carries.
"""

import re

from skyportal.app_server import skyportal_handlers
from skyportal.handlers.api import (
    BrokerAlertsHandler,
    BrokerCutoutsHandler,
    BrokerObjectHandler,
    BrokerPhotometryHandler,
    BrokerSaveHandler,
)


def route_for(path):
    """The handler and captured groups the route table gives this path."""
    for pattern, handler, *_ in skyportal_handlers:
        match = re.fullmatch(pattern, path)
        if match:
            return handler, match.groups()
    return None, None


def test_objects_route_reaches_the_object_handler():
    assert route_for("/api/brokers/1/objects/ZTF1") == (
        BrokerObjectHandler,
        ("1", "ZTF1"),
    )


def test_photometry_and_save_take_an_object_id_under_either_spelling():
    for base in ("objects", "alerts"):
        assert route_for(f"/api/brokers/1/{base}/ZTF1/photometry") == (
            BrokerPhotometryHandler,
            ("1", "ZTF1"),
        )
        assert route_for(f"/api/brokers/1/{base}/ZTF1/save") == (
            BrokerSaveHandler,
            ("1", "ZTF1"),
        )


def test_cutouts_route_reaches_the_cutouts_handler():
    assert route_for("/api/brokers/1/alerts/123456789/cutouts") == (
        BrokerCutoutsHandler,
        ("1", "123456789"),
    )


def test_bare_alerts_route_captures_no_object_id():
    assert route_for("/api/brokers/1/alerts") == (BrokerAlertsHandler, ("1",))


def test_alerts_path_form_reaches_the_object_handler():
    assert route_for("/api/brokers/1/alerts/ZTF1") == (
        BrokerObjectHandler,
        ("1", "ZTF1"),
    )
