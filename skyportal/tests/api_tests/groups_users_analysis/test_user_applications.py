import uuid

import sqlalchemy as sa

from skyportal.models import DBSession, Invitation, User, UserNotification
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


def test_an_endorser_who_cannot_decide_is_not_the_one_notified(
    view_only_user, super_admin_user
):
    """Naming someone who may not act on applications must not put the
    application in their lap; it goes to the administrators who can."""
    session = DBSession()
    session.rollback()
    last_notification_id = (
        session.scalar(sa.select(sa.func.max(UserNotification.id))) or 0
    )

    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(endorser_email=view_only_user.contact_email, email=email)[0] == 200

    session.rollback()
    notified = session.scalars(
        sa.select(UserNotification.user_id).where(
            UserNotification.id > last_notification_id,
            UserNotification.notification_type == "user_application",
        )
    ).all()
    assert notified
    assert view_only_user.id not in notified
    assert all(
        "Manage users" in session.get(User, user_id).permissions for user_id in notified
    )


def pending_application_id(token, email):
    status, data = api(
        "GET",
        "user_applications",
        params={"status": "pending", "numPerPage": 100},
        token=token,
    )
    assert status == 200
    return find(data["data"]["applications"], email)["id"]


def test_chosen_streams_reach_the_invitation(
    endorse_users_token, public_group, public_stream, public_streamuser
):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    application_id = pending_application_id(endorse_users_token, email)

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={
            "status": "endorsed",
            "streamIDs": [public_stream.id],
            "groupIDs": [public_group.id],
        },
        token=endorse_users_token,
    )
    assert status == 200, data

    invitation = DBSession().scalar(
        sa.select(Invitation).where(Invitation.id == data["data"]["invitation_id"])
    )
    assert [stream.id for stream in invitation.streams] == [public_stream.id]


def test_a_group_whose_stream_is_not_granted_is_refused(
    endorse_users_token, public_group, public_streamuser
):
    # public_group reads public_stream; endorsing into it while granting no
    # streams would leave the applicant in a group whose data they cannot read.
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    application_id = pending_application_id(endorse_users_token, email)

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "endorsed", "streamIDs": [], "groupIDs": [public_group.id]},
        token=endorse_users_token,
    )
    assert status == 400
    assert "does not grant" in data["message"]


def test_endorser_cannot_grant_a_stream_they_do_not_have(
    endorse_users_token, public_stream2
):
    email = f"{uuid.uuid4().hex}@example.org"
    assert submit(email=email)[0] == 200
    application_id = pending_application_id(endorse_users_token, email)

    status, data = api(
        "PATCH",
        f"user_applications/{application_id}",
        data={"status": "endorsed", "streamIDs": [public_stream2.id]},
        token=endorse_users_token,
    )
    assert status == 400
    assert "streams you have yourself" in data["message"]
