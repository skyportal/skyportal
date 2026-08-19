import asyncio
import uuid

import pytest
import sqlalchemy as sa
from skyportal_py import SkyPortalError
from skyportal_py.followup_requests import (
    DefaultFollowupRequestPost,
    FollowupRequestPost,
)

from skyportal.tests import client

from ....utils.naive_datetime import utcnow_naive


def test_token_user_post_robotic_followup_request(
    public_group_sedm_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    sp = client(upload_data_token)
    id = sp.post_followup_request(FollowupRequestPost(**request_data)).id

    followup_request = sp.fetch_followup_request(id)

    for key in request_data:
        assert getattr(followup_request, key) == request_data[key]


def test_gemini_followup_blank_note_title(
    public_group_gemini_allocation, public_source, upload_data_token
):
    # Regression guard: a blank note title must not crash the Gemini submit.
    # An unset optional param became None and yarl rejected it in `params=`.
    request_data = {
        "allocation_id": public_group_gemini_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "template_ids": "21",
            "start_date": "2026-05-08 04:00:00",
            "end_date": "2026-05-08 05:00:00",
            "l_exptime": 0,
            "l_elmin": 1.0,
            "l_elmax": 1.6,
            "note_title": "",
        },
    }

    client(upload_data_token).post_followup_request(FollowupRequestPost(**request_data))


def test_winter_followup_submit(
    public_group_winter_allocation, public_source, upload_data_token
):
    # Regression guard: the submit_trigger flag (a bool) must not crash the
    # WINTER submit (yarl rejects bool in aiohttp params=).
    request_data = {
        "allocation_id": public_group_winter_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "filter": "J",
            "start_date": "2026-05-08 04:00:00",
            "end_date": "2026-05-08 05:00:00",
        },
    }

    client(upload_data_token).post_followup_request(FollowupRequestPost(**request_data))


def test_token_user_delete_owned_followup_request(
    public_group_generic_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_generic_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_choices": public_group_generic_allocation.instrument.to_dict()[
                "filters"
            ],
            "exposure_time": 300,
            "exposure_counts": 1,
            "maximum_airmass": 2,
            "minimum_lunar_distance": 30,
        },
    }

    sp = client(upload_data_token)
    id = sp.post_followup_request(FollowupRequestPost(**request_data)).id

    sp.delete_followup_request(id)


def test_token_user_modify_owned_followup_request(
    public_group_sedm_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    sp = client(upload_data_token)
    id = sp.post_followup_request(FollowupRequestPost(**request_data)).id

    new_request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 4,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    sp.update_followup_request(id, **new_request_data)

    followup_request = sp.fetch_followup_request(id)

    for k in new_request_data:
        assert getattr(followup_request, k) == new_request_data[k]


def test_regular_user_delete_super_admin_followup_request(
    public_group_generic_allocation,
    public_source,
    upload_data_token,
    super_admin_token,
):
    request_data = {
        "allocation_id": public_group_generic_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_choices": public_group_generic_allocation.instrument.to_dict()[
                "filters"
            ],
            "exposure_time": 300,
            "exposure_counts": 1,
            "maximum_airmass": 2,
            "minimum_lunar_distance": 30,
        },
    }

    id = (
        client(super_admin_token)
        .post_followup_request(FollowupRequestPost(**request_data))
        .id
    )

    client(upload_data_token).delete_followup_request(id)


def test_group1_user_cannot_see_group2_followup_request(
    public_group2_sedm_allocation,
    public_source_group2,
    super_admin_token,
    view_only_token,
):
    request_data = {
        "allocation_id": public_group2_sedm_allocation.id,
        "obj_id": public_source_group2.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    id = (
        client(super_admin_token)
        .post_followup_request(FollowupRequestPost(**request_data))
        .id
    )

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_followup_request(id)
    assert err.value.status_code == 400

    page = client(view_only_token).fetch_followup_requests()
    assert id not in [a.id for a in page.followup_requests]


def test_filter_followup_request(
    public_group_sedm_allocation,
    public_source,
    upload_data_token,
    view_only_token,
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    time_before_post = utcnow_naive().isoformat()
    client(upload_data_token).post_followup_request(FollowupRequestPost(**request_data))

    page = client(view_only_token).fetch_followup_requests(start_date=time_before_post)
    assert any(s.obj_id == public_source.id for s in page.followup_requests)

    time_after_post = utcnow_naive().isoformat()

    page = client(view_only_token).fetch_followup_requests(start_date=time_after_post)
    assert not any(s.obj_id == public_source.id for s in page.followup_requests)

    page = client(view_only_token).fetch_followup_requests(source_id=public_source.id)
    assert any(s.obj_id == public_source.id for s in page.followup_requests)


def _default_followup_payload(public_group, allocation, **extra):
    data = {
        "allocation_id": allocation.id,
        "default_followup_name": str(uuid.uuid4()),
        "source_filter": {"name": ".*", "group_id": public_group.id},
        "target_group_ids": [public_group.id],
        "payload": {
            "priority": 5,
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }
    data.update(extra)
    return data


def test_default_followup_request_stores_constraints(
    public_group, public_group_sedm_allocation, super_admin_token
):
    request_data = _default_followup_payload(
        public_group,
        public_group_sedm_allocation,
        not_if_classified=True,
        not_if_duplicates=True,
        radius=2.0,
        priority_order="desc",
        validity_days=3,
        comment="auto-trigger test",
        implements_update=False,
    )

    sp = client(super_admin_token)
    new_id = sp.post_default_followup_request(
        DefaultFollowupRequestPost(**request_data)
    ).id

    requests = sp.fetch_default_followup_requests()
    match = next(r for r in requests if r.id == new_id)
    constraints = match.constraints
    assert constraints is not None
    assert constraints["not_if_classified"] is True
    assert constraints["not_if_duplicates"] is True
    # radius is always added alongside any other constraint
    assert constraints["radius"] == 2.0
    # constraints not supplied are absent (not defaulted)
    assert "not_if_spectra_exist" not in constraints
    # priority_order / validity_days / comment are stored for the auto-trigger path
    assert match.priority_order == "desc"
    assert match.validity_days == 3
    assert match.comment == "auto-trigger test"
    assert match.implements_update is False


def test_default_followup_request_source_filter_regex_validation(
    public_group, public_group_sedm_allocation, super_admin_token
):
    def make(name):
        return DefaultFollowupRequestPost(
            **_default_followup_payload(
                public_group,
                public_group_sedm_allocation,
                source_filter={"name": name, "group_id": public_group.id},
            )
        )

    sp = client(super_admin_token)

    # A valid regex is accepted.
    sp.post_default_followup_request(make("^ZTF2[0-9].*"))

    # A malformed regex is rejected at creation (would otherwise error in
    # Postgres on every source save).
    with pytest.raises(SkyPortalError, match="valid regular expression") as err:
        sp.post_default_followup_request(make("([unterminated"))
    assert err.value.status_code == 400

    # A catastrophic-backtracking pattern is rejected at creation (ReDoS guard).
    with pytest.raises(SkyPortalError, match="catastrophic backtracking") as err:
        sp.post_default_followup_request(make("(a+)+$"))
    assert err.value.status_code == 400

    # An oversized pattern is rejected.
    with pytest.raises(SkyPortalError, match="at most") as err:
        sp.post_default_followup_request(make("a" * 1001))
    assert err.value.status_code == 400


def test_default_followup_request_without_constraints_is_null(
    public_group, public_group_sedm_allocation, super_admin_token
):
    request_data = _default_followup_payload(public_group, public_group_sedm_allocation)

    sp = client(super_admin_token)
    new_id = sp.post_default_followup_request(
        DefaultFollowupRequestPost(**request_data)
    ).id

    requests = sp.fetch_default_followup_requests()
    match = next(r for r in requests if r.id == new_id)
    # no constraint keys supplied -> stored as null (always submit)
    assert match.constraints is None


def test_auto_followup_request_flushes_before_submit(
    public_group_generic_allocation, super_admin_user
):
    # The auto-followup path (refresh_source=False) must flush the new request
    # before the facility submit() re-queries it by id; otherwise submit() gets
    # None -> "'NoneType' object has no attribute 'obj'". Call it directly: the
    # DefaultFollowupRequest firing path runs via run_async, whose executor
    # thread lacks the async session factory under the test harness.
    from baselayer.app import models as baselayer_models
    from skyportal.handlers.api.followup_request import post_followup_request_async
    from skyportal.models import DBSession, FollowupRequest, Obj, User
    from skyportal.tests.fixtures import ObjFactory

    alloc = public_group_generic_allocation
    obj = ObjFactory(groups=[alloc.group])
    DBSession().commit()
    obj_id = obj.id
    data = {
        "obj_id": obj_id,
        "allocation_id": alloc.id,
        "requester_id": super_admin_user.id,
        "last_modified_by_id": super_admin_user.id,
        "target_group_ids": [alloc.group_id],
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_choices": alloc.instrument.to_dict()["filters"],
            "exposure_time": 300,
            "exposure_counts": 1,
            "maximum_airmass": 2,
            "minimum_lunar_distance": 30,
        },
    }

    async def _run():
        async with baselayer_models.async_plain_session_factory() as session:
            session.user_or_token = await session.get(User, super_admin_user.id)
            await post_followup_request_async(data, None, session, refresh_source=False)
            await session.commit()

    asyncio.run(_run())

    DBSession().expire_all()
    followup_request = DBSession().scalar(
        sa.select(FollowupRequest).where(
            FollowupRequest.obj_id == obj_id,
            FollowupRequest.allocation_id == alloc.id,
        )
    )
    try:
        assert followup_request is not None, "auto-followup request was not created"
        # Without the flush fix, submit() re-queries a None id -> None.obj.
        assert "NoneType" not in (followup_request.status or ""), (
            followup_request.status
        )
        assert followup_request.status == "submitted", followup_request.status
    finally:
        if followup_request is not None:
            DBSession().delete(followup_request)
        DBSession().execute(sa.delete(Obj).where(Obj.id == obj_id))
        DBSession().commit()
