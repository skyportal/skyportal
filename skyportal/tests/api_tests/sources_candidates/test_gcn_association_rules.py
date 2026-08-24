"""The per-user cuts that decide which event pairs count as coincident."""

from skyportal.tests import api


def _rules(token):
    status, data = api("GET", "gcn_association_rules", token=token)
    assert status == 200, data
    return data["data"]


def test_association_rule_round_trip(super_admin_token, public_group):
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "group_id": public_group.id,
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
            "group_id": public_group.id,
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


def test_association_rule_rejects_a_bad_messenger(super_admin_token, public_group):
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "group_id": public_group.id,
            "detector_type_1": "gravitational-wave",
            "detector_type_2": "gamma-rays-maybe",
            "days": 1.0,
        },
        token=super_admin_token,
    )
    assert status == 400, data


def test_association_rules_are_scoped_to_their_group(
    super_admin_token, view_only_token, public_group2
):
    """A group's cuts are its own: someone outside it cannot see them.

    Members can, which is the point of putting them on the group -- an EM-GW
    group maintains one set of cuts between them.
    """
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "group_id": public_group2.id,
            "detector_type_1": "x-ray",
            "detector_type_2": "gravitational-wave",
            "days": 2.0,
        },
        token=super_admin_token,
    )
    assert status == 200, data
    rule_id = data["data"]["id"]

    # the view-only user is not in public_group2
    assert not [r for r in _rules(view_only_token) if r["id"] == rule_id], (
        "a rule was visible to someone outside its group"
    )
    # ... while a member (here, the super admin who made it) sees it
    assert [r for r in _rules(super_admin_token) if r["id"] == rule_id]

    api("DELETE", f"gcn_association_rules/{rule_id}", token=super_admin_token)
