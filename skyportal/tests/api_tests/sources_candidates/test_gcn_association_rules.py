"""The per-user cuts that decide which event pairs count as coincident."""

from skyportal.tests import api


def _rules(token):
    status, data = api("GET", "gcn_association_rules", token=token)
    assert status == 200, data
    return data["data"]


def test_association_rule_round_trip(super_admin_token):
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "detector_type_1": "neutrino",
            "detector_type_2": "gravitational-wave",
            "days": 0.0001,
            "min_consistency": 0.75,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    rule_id = data["data"]["id"]

    mine = [r for r in _rules(super_admin_token) if r["id"] == rule_id]
    assert mine, "the rule was not returned"
    rule = mine[0]
    # stored sorted, so the pair is one row however it was entered
    assert rule["detector_type_1"] == "gravitational-wave"
    assert rule["detector_type_2"] == "neutrino"
    assert rule["days"] == 0.0001
    assert rule["min_consistency"] == 0.75

    # posting the same pair replaces rather than duplicates
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "detector_type_1": "gravitational-wave",
            "detector_type_2": "neutrino",
            "days": 0.5,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["id"] == rule_id, "a duplicate rule was created"
    rule = [r for r in _rules(super_admin_token) if r["id"] == rule_id][0]
    assert rule["days"] == 0.5

    status, data = api(
        "DELETE", f"gcn_association_rules/{rule_id}", token=super_admin_token
    )
    assert status == 200, data
    assert not [r for r in _rules(super_admin_token) if r["id"] == rule_id]


def test_association_rule_rejects_a_bad_messenger(super_admin_token):
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "detector_type_1": "gravitational-wave",
            "detector_type_2": "gamma-rays-maybe",
            "days": 1.0,
        },
        token=super_admin_token,
    )
    assert status == 400, data


def test_association_rules_are_private(super_admin_token, view_only_token):
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "detector_type_1": "x-ray",
            "detector_type_2": "gravitational-wave",
            "days": 2.0,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    rule_id = data["data"]["id"]

    assert not [r for r in _rules(view_only_token) if r["id"] == rule_id], (
        "another user's rule was visible"
    )


def test_association_rule_tags_travel_with_their_messenger(super_admin_token):
    """A rule can require tags, e.g. only BNS/NSBH gravitational waves.

    The pair is stored sorted, so the tag lists have to be sorted with it --
    otherwise the BNS requirement would end up on the GRB side.
    """
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            # deliberately entered in the order that gets swapped on save
            "detector_type_1": "neutrino",
            "detector_type_2": "gravitational-wave",
            "tags_1": ["IceCube"],
            "tags_2": ["BNS", "NSBH"],
            "days": 0.001,
            "min_consistency": 0.5,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    rule_id = data["data"]["id"]

    status, data = api("GET", "gcn_association_rules", token=super_admin_token)
    assert status == 200, data
    rule = [r for r in data["data"] if r["id"] == rule_id][0]

    assert rule["detector_type_1"] == "gravitational-wave"
    assert rule["tags_1"] == ["BNS", "NSBH"], (
        "the tags did not follow their messenger when the pair was sorted"
    )
    assert rule["detector_type_2"] == "neutrino"
    assert rule["tags_2"] == ["IceCube"]

    api("DELETE", f"gcn_association_rules/{rule_id}", token=super_admin_token)
