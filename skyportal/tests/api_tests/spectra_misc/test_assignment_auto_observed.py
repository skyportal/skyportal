"""An uploaded spectrum closes out the observing-run assignment it satisfies."""

import pytest
import sqlalchemy as sa

from skyportal.models import ClassicalAssignment, DBSession
from skyportal.tests import api

# red_transients_run, the run behind public_assignment, sits on this date.
RUN_DATE = "3021-02-27"


@pytest.fixture()
def posted_spectra(super_admin_token):
    """Spectra posted through the API, deleted so the fixtures can tear down."""
    ids = []
    yield ids
    for spectrum_id in ids:
        api("DELETE", f"spectrum/{spectrum_id}", token=super_admin_token)


def _post_spectrum(obj_id, instrument_id, observed_at, group_id, token, posted):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": obj_id,
            "observed_at": observed_at,
            "instrument_id": instrument_id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200, data
    posted.append(data["data"]["id"])
    return data["data"]["id"]


def _status_of(assignment_id):
    DBSession().expire_all()
    return DBSession().scalar(
        sa.select(ClassicalAssignment.status).where(
            ClassicalAssignment.id == assignment_id
        )
    )


def test_spectrum_on_the_run_date_marks_the_assignment_done(
    public_source, public_assignment, public_group, super_admin_token, posted_spectra
):
    assert _status_of(public_assignment.id) == "pending"

    _post_spectrum(
        public_source.id,
        public_assignment.run.instrument.id,
        f"{RUN_DATE}T08:00:00",
        public_group.id,
        super_admin_token,
        posted_spectra,
    )

    assert _status_of(public_assignment.id) == "done"


def test_spectrum_after_midnight_is_still_within_the_window(
    public_source, public_assignment, public_group, super_admin_token, posted_spectra
):
    """A run's date is the local night, so the exposure can land on the next day."""
    _post_spectrum(
        public_source.id,
        public_assignment.run.instrument.id,
        "3021-02-28T06:00:00",
        public_group.id,
        super_admin_token,
        posted_spectra,
    )

    assert _status_of(public_assignment.id) == "done"


def test_spectrum_from_another_instrument_leaves_the_assignment_alone(
    public_source,
    public_assignment,
    public_group,
    lris,
    super_admin_token,
    posted_spectra,
):
    _post_spectrum(
        public_source.id,
        lris.id,
        f"{RUN_DATE}T08:00:00",
        public_group.id,
        super_admin_token,
        posted_spectra,
    )

    assert _status_of(public_assignment.id) == "pending"


def test_spectrum_outside_the_window_leaves_the_assignment_alone(
    public_source, public_assignment, public_group, super_admin_token, posted_spectra
):
    _post_spectrum(
        public_source.id,
        public_assignment.run.instrument.id,
        "3021-03-05T08:00:00",
        public_group.id,
        super_admin_token,
        posted_spectra,
    )

    assert _status_of(public_assignment.id) == "pending"


def test_an_explicit_verdict_is_never_overwritten(
    public_source, public_assignment, public_group, super_admin_token, posted_spectra
):
    """Someone who said "not done" has decided; a later spectrum must not undo it."""
    assignment = DBSession().scalar(
        sa.select(ClassicalAssignment).where(
            ClassicalAssignment.id == public_assignment.id
        )
    )
    assignment.status = "not done"
    DBSession().commit()

    _post_spectrum(
        public_source.id,
        public_assignment.run.instrument.id,
        f"{RUN_DATE}T08:00:00",
        public_group.id,
        super_admin_token,
        posted_spectra,
    )

    assert _status_of(public_assignment.id) == "not done"
