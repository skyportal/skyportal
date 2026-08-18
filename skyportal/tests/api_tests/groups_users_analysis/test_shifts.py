import uuid
from datetime import date, datetime, timedelta

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.shifts import ShiftPost

from skyportal.tests import client


def test_shift(public_group, super_admin_token, view_only_token, super_admin_user):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    shift_post = ShiftPost(
        name=name,
        group_id=public_group.id,
        start_date=start_date,
        end_date=end_date,
        description="the Night Shift",
        shift_admins=[super_admin_user.id],
        required_users_number=2,
    )
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_shift(shift_post)
    assert err.value.status_code == 401

    sp = client(super_admin_token)
    shift_id = sp.post_shift(shift_post).id

    sp.fetch_shift(shift_id)

    shifts = sp.fetch_shifts(group_id=public_group.id)

    assert any(shift_post.name == s.name for s in shifts)
    assert any(
        datetime.fromisoformat(shift_post.start_date) == s.start_date for s in shifts
    )
    assert any(
        datetime.fromisoformat(shift_post.end_date) == s.end_date for s in shifts
    )
    assert any(
        shift_post.required_users_number == s.required_users_number for s in shifts
    )

    assert any(
        len([s for s in shift.shift_users_ids if s == super_admin_user.id]) == 1
        for shift in shifts
    )

    name2 = str(uuid.uuid4())
    description2 = "the Day Shift"
    required_users_number2 = 3

    sp.update_shift(
        shift_id,
        name=name2,
        description=description2,
        required_users_number=required_users_number2,
    )

    shift = sp.fetch_shift(shift_id)

    assert shift.name == name2
    assert shift.description == description2
    assert shift.required_users_number == required_users_number2


def test_shift_summary(
    public_group, super_admin_token, super_admin_user, gcn_GRB180116A
):
    sp = client(super_admin_token)
    # add a shift to the group, with a start day one day before today,
    # and an end day one day after today
    shift_name_1 = str(uuid.uuid4())
    start_date = "2018-01-15T12:00:00"
    end_date = "2018-01-17T12:00:00"
    shift_id = sp.post_shift(
        ShiftPost(
            name=shift_name_1,
            group_id=public_group.id,
            start_date=start_date,
            end_date=end_date,
            description="Shift during GCN",
            shift_admins=[super_admin_user.id],
        )
    ).id

    sp.fetch_shift(shift_id)

    shift_name_2 = str(uuid.uuid4())
    start_date = "2018-01-17T12:00:00"
    end_date = "2018-01-18T12:00:00"
    shift_id_2 = sp.post_shift(
        ShiftPost(
            name=shift_name_2,
            group_id=public_group.id,
            start_date=start_date,
            end_date=end_date,
            description="Shift not during GCN",
            shift_admins=[super_admin_user.id],
        )
    ).id

    sp.fetch_shifts(group_id=public_group.id)

    dateobs = gcn_GRB180116A.dateobs.strftime("%Y-%m-%dT%H:%M:%S")

    report = sp.fetch_shift_summary(shift_id)
    assert int(report.shifts.total) == 1
    assert int(report.gcns.total) == 1
    assert report.shifts.data[0]["name"] == shift_name_1
    assert report.gcns.data[0]["dateobs"] == dateobs
    assert shift_id in report.gcns.data[0]["shift_ids"]
    assert shift_id_2 not in report.gcns.data[0]["shift_ids"]

    report = sp.fetch_shift_summary(
        start_date="2018-01-14T12:00:00", end_date="2018-01-19T12:00:00"
    )

    assert int(report.shifts.total) == 2
    assert int(report.gcns.total) == 1
    assert shift_id in report.gcns.data[0]["shift_ids"]
    assert shift_id_2 not in report.gcns.data[0]["shift_ids"]
