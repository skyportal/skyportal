from skyportal.model_util import resolve_deployed_feedback
from skyportal.models import DBSession, Feedback
from skyportal.tests import api
from skyportal.utils.gitlog import running_pr_urls

PR = "https://github.com/skyportal/skyportal/pull"


def test_feedback(view_only_token, view_only_token2, super_admin_token):
    status, data = api(
        "POST",
        "feedback",
        data={"category": "bug", "text": "The button is broken"},
        token=view_only_token,
    )
    assert status == 200
    feedback_id = data["data"]["id"]

    status, data = api("GET", "feedback", token=view_only_token)
    assert status == 200
    assert feedback_id in [m["id"] for m in data["data"]["messages"]]

    status, data = api("GET", "feedback", token=view_only_token2)
    assert status == 200
    assert feedback_id not in [m["id"] for m in data["data"]["messages"]]

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"resolved": True},
        token=view_only_token,
    )
    assert status == 403

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"resolved": True},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api("GET", f"feedback/{feedback_id}", token=super_admin_token)
    assert data["data"]["messages"][0]["resolved"]


def test_feedback_replies(view_only_token, view_only_token2, super_admin_token):
    status, data = api(
        "POST",
        "feedback",
        data={"category": "change", "text": "Please add a dark mode"},
        token=view_only_token,
    )
    assert status == 200
    feedback_id = data["data"]["id"]

    status, _ = api(
        "POST",
        f"feedback/{feedback_id}/replies",
        data={"text": "Not my message"},
        token=view_only_token2,
    )
    assert status == 400

    status, _ = api(
        "POST",
        f"feedback/{feedback_id}/replies",
        data={"text": "It already exists, in your profile"},
        token=super_admin_token,
    )
    assert status == 200

    status, _ = api(
        "POST",
        f"feedback/{feedback_id}/replies",
        data={"text": "Found it, thanks"},
        token=view_only_token,
    )
    assert status == 200

    status, data = api("GET", f"feedback/{feedback_id}", token=view_only_token)
    assert status == 200
    replies = data["data"]["messages"][0]["replies"]
    assert [r["text"] for r in replies] == [
        "It already exists, in your profile",
        "Found it, thanks",
    ]


def test_feedback_rejects_unknown_category(view_only_token):
    status, _ = api(
        "POST",
        "feedback",
        data={"category": "praise", "text": "Nice"},
        token=view_only_token,
    )
    assert status == 400


def test_feedback_assignee(view_only_token, super_admin_token, super_admin_user):
    status, data = api(
        "POST",
        "feedback",
        data={"category": "bug", "text": "The plot is empty"},
        token=view_only_token,
    )
    assert status == 200
    feedback_id = data["data"]["id"]

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"assignee_id": super_admin_user.id},
        token=view_only_token,
    )
    assert status == 403

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"assignee_id": super_admin_user.id},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api("GET", f"feedback/{feedback_id}", token=view_only_token)
    message = data["data"]["messages"][0]
    assert message["assignee"]["id"] == super_admin_user.id
    assert not message["resolved"]

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={"assignee_id": None},
        token=super_admin_token,
    )
    assert status == 200
    status, data = api("GET", f"feedback/{feedback_id}", token=super_admin_token)
    assert data["data"]["messages"][0]["assignee"] is None


def test_feedback_pull_requests(view_only_token, super_admin_token):
    status, data = api(
        "POST",
        "feedback",
        data={"category": "bug", "text": "The legend overlaps the plot"},
        token=view_only_token,
    )
    feedback_id = data["data"]["id"]
    already_deployed = sorted(running_pr_urls())[0]

    for pr_urls in (
        ["https://github.com/skyportal/skyportal/issues/12"],
        ["https://github.com/skyportal/baselayer/pull/12"],
    ):
        status, _ = api(
            "PATCH",
            f"feedback/{feedback_id}",
            data={"pr_urls": pr_urls},
            token=super_admin_token,
        )
        assert status == 400

    status, _ = api(
        "PATCH",
        f"feedback/{feedback_id}",
        data={
            "pr_urls": [
                f"{PR}/999999/files",
                f"{PR.replace('skyportal/skyportal', 'SkyPortal/skyportal')}/999999",
                already_deployed,
            ]
        },
        token=super_admin_token,
    )
    assert status == 200

    status, data = api("GET", f"feedback/{feedback_id}", token=view_only_token)
    message = data["data"]["messages"][0]
    assert message["pull_requests"] == [
        {"url": f"{PR}/999999", "deployed": False},
        {"url": already_deployed, "deployed": True},
    ]
    assert message["deployed_at"] is None


def test_resolve_deployed_feedback(view_only_token, super_admin_token):
    ids = []
    for pr_urls in ([f"{PR}/999001", f"{PR}/999002"], [f"{PR}/999003"]):
        status, data = api(
            "POST",
            "feedback",
            data={"category": "bug", "text": "Something is off"},
            token=view_only_token,
        )
        ids.append(data["data"]["id"])
        status, _ = api(
            "PATCH",
            f"feedback/{ids[-1]}",
            data={"pr_urls": pr_urls},
            token=super_admin_token,
        )
        assert status == 200
    both, other = ids

    def deploy(*numbers):
        session = DBSession()
        resolved = resolve_deployed_feedback(
            session, [{"pr_url": f"{PR}/{n}"} for n in numbers]
        )
        session.commit()
        return resolved

    # only one of its two pull requests is deployed
    resolved = deploy(999001)
    assert both not in resolved and other not in resolved
    assert not DBSession().get(Feedback, both).resolved

    # resolved by hand beforehand: its author is still told it is deployed
    api("PATCH", f"feedback/{other}", data={"resolved": True}, token=super_admin_token)
    resolved = deploy(999001, 999002, 999003)
    assert both in resolved and other in resolved
    for feedback_id in (both, other):
        message = DBSession().get(Feedback, feedback_id)
        DBSession().refresh(message)
        assert message.resolved and message.deployed_at is not None

    # notified once, and a rollback does not reopen it
    api("PATCH", f"feedback/{both}", data={"resolved": False}, token=super_admin_token)
    assert both not in deploy(999001, 999002) + deploy()
    message = DBSession().get(Feedback, both)
    DBSession().refresh(message)
    assert not message.resolved
