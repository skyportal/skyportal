from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from skyportal.models import DBSession, Role, UserNotification
from skyportal.tests import api, retry_until
from skyportal.tests.fixtures import UserFactory


def _new_spectra_subscriber(group, stream, expiration_date=None):
    user = UserFactory(
        groups=[group],
        roles=[DBSession().scalar(sa.select(Role).where(Role.id == "Full user"))],
        streams=[stream],
    )
    user.preferences = {
        "notifications": {"sources": {"active": True, "new_spectra": True}}
    }
    user.expiration_date = expiration_date
    DBSession().commit()
    return user.id


def _spectrum_notifications(user_id):
    DBSession().expire_all()
    return (
        DBSession()
        .scalars(
            sa.select(UserNotification).where(
                UserNotification.user_id == user_id,
                UserNotification.notification_type == "sources_new_spectrum",
            )
        )
        .all()
    )


def test_expired_users_are_not_notified(
    public_group, public_stream, public_source, lris, upload_data_token
):
    active_id = _new_spectra_subscriber(public_group, public_stream)
    expired_id = _new_spectra_subscriber(
        public_group, public_stream, datetime.now() - timedelta(days=1)
    )
    spectrum_id = None
    try:
        status, data = api(
            "POST",
            "spectrum",
            data={
                "obj_id": public_source.id,
                "observed_at": str(datetime.now(UTC)),
                "instrument_id": lris.id,
                "wavelengths": [664, 665, 666],
                "fluxes": [234.2, 232.1, 235.3],
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200, data
        spectrum_id = data["data"]["id"]

        def active_user_notified():
            assert _spectrum_notifications(active_id)

        retry_until(active_user_notified)
        assert _spectrum_notifications(expired_id) == []
    finally:
        if spectrum_id is not None:
            api("DELETE", f"spectrum/{spectrum_id}", token=upload_data_token)
        UserFactory.teardown(active_id)
        UserFactory.teardown(expired_id)
