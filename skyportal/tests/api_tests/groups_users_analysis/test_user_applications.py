import uuid

from skyportal.tests import api


def submit(endorser_email=None, email=None):
    """Apply for an account the way the /apply page does: no token."""
    return api(
        "POST",
        "user_applications",
        data={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": email or f"{uuid.uuid4().hex}@example.org",
            "affiliation": "Analytical Engine Co.",
            "statement": "I would like to scan candidates.",
            "endorserEmail": endorser_email,
        },
    )


def find(applications, application_email):
    return next(
        (a for a in applications if a["contact_email"] == application_email), None
    )


def test_apply_without_token_then_endorser_sees_it(endorse_users_token):
    email = f"{uuid.uuid4().hex}@example.org"
    status, data = submit(email=email)
    assert status == 200

    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    assert status == 200
    application = find(data["data"]["applications"], email)
    assert application is not None
    assert application["first_name"] == "Ada"
    assert application["affiliation"] == "Analytical Engine Co."


def test_application_queue_refuses_a_user_who_cannot_decide(view_only_token):
    status, data = api("GET", "user_applications", token=view_only_token)
    assert status == 403
    assert "Insufficient permissions" in data["message"]


def test_user_admins_decide_alongside_peer_endorsers(manage_users_token):
    """`Manage users` acts on applications in either mode; `Endorse users` is
    the addition peer endorsement makes (test_config turns it on)."""
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200

    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=manage_users_token,
    )
    assert status == 200
    application_id = find(data["data"]["applications"], email)["id"]

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "endorsed"},
        token=manage_users_token,
    )
    assert status == 200
    assert data["data"]["invitation_id"] is not None


def test_resubmitting_does_not_queue_a_second_application(endorse_users_token):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    assert submit(email=email)[0] == 200

    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    assert status == 200
    matches = [a for a in data["data"]["applications"] if a["contact_email"] == email]
    assert len(matches) == 1


def test_named_endorser_is_resolved_to_their_account(endorse_users_token, user):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(endorser_email=user.contact_email, email=email)[0] == 200

    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "mine": "true", "numPerPage": 100},
        token=endorse_users_token,
    )
    assert status == 200
    application = find(data["data"]["applications"], email)
    assert application is not None
    assert application["endorser"]["id"] == user.id


def test_endorsing_issues_an_invitation(endorse_users_token, public_group):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200

    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    application_id = find(data["data"]["applications"], email)["id"]

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "endorsed", "groupIDs": [public_group.id]},
        token=endorse_users_token,
    )
    assert status == 200
    invitation_id = data["data"]["invitation_id"]

    status, data = api(
        "GET", f"user_applications/{application_id}", token=endorse_users_token
    )
    assert status == 200
    assert data["data"]["status"] == "endorsed"
    assert data["data"]["invitation_id"] == invitation_id


def test_endorsing_twice_is_refused(endorse_users_token):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    application_id = find(data["data"]["applications"], email)["id"]

    assert (
        api(
            "PATCH",
            f"user_applications/{application_id}",
            data={"status": "endorsed"},
            token=endorse_users_token,
        )[0]
        == 200
    )
    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "endorsed"},
        token=endorse_users_token,
    )
    assert status == 400
    assert "already been endorsed" in data["message"]


def test_endorser_cannot_grant_a_group_they_are_not_in(
    endorse_users_token, public_group2
):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    application_id = find(data["data"]["applications"], email)["id"]

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "endorsed", "groupIDs": [public_group2.id]},
        token=endorse_users_token,
    )
    assert status == 400
    assert "groups you belong to" in data["message"]


def test_declining_records_the_reason(endorse_users_token):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    application_id = find(data["data"]["applications"], email)["id"]

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "declined", "declineReason": "Not known to us"},
        token=endorse_users_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"user_applications/{application_id}", token=endorse_users_token
    )
    assert status == 200
    assert data["data"]["status"] == "declined"
    assert data["data"]["decline_reason"] == "Not known to us"


def test_delete_application(endorse_users_token):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=endorse_users_token,
    )
    application_id = find(data["data"]["applications"], email)["id"]

    assert (
        api("DELETE", f"user_applications/{application_id}", token=endorse_users_token)[
            0
        ]
        == 200
    )
    assert (
        api("GET", f"user_applications/{application_id}", token=endorse_users_token)[0]
        == 400
    )
