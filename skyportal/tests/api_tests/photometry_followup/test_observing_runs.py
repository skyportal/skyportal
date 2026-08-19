import pytest
from skyportal_py import SkyPortalError
from skyportal_py.observing_runs import ObservingRunPost, ObservingRunUpdate
from skyportal_py.photometry import PhotometryPost
from skyportal_py.sources import SourcePost

from skyportal.tests import client


def test_token_user_add_new_observing_run(
    lris, observing_run_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    sp = client(observing_run_token)
    run_id = sp.post_observing_run(ObservingRunPost(**run_details)).id

    run = sp.fetch_observing_run(run_id)
    for key in run_details:
        value = getattr(run, key)
        if key == "calendar_date":
            value = value.isoformat()
        assert value == run_details[key]


def test_super_admin_user_delete_nonowned_observing_run(
    lris, observing_run_token, super_admin_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    run_id = (
        client(observing_run_token)
        .post_observing_run(ObservingRunPost(**run_details))
        .id
    )

    client(super_admin_token).delete_observing_run(run_id)


def test_unauthorized_user_delete_nonowned_observing_run(
    lris, observing_run_token, manage_sources_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    run_id = (
        client(observing_run_token)
        .post_observing_run(ObservingRunPost(**run_details))
        .id
    )

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).delete_observing_run(run_id)
    assert err.value.status_code == 400


def test_authorized_user_modify_owned_observing_run(
    lris, observing_run_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    sp = client(observing_run_token)
    run_id = sp.post_observing_run(ObservingRunPost(**run_details)).id

    new_date = {"calendar_date": "2020-02-17"}
    run_details.update(new_date)

    sp.update_observing_run(run_id, ObservingRunUpdate(**new_date))

    run = sp.fetch_observing_run(run_id)
    for key in run_details:
        value = getattr(run, key)
        if key == "calendar_date":
            value = value.isoformat()
        assert value == run_details[key]


def test_unauthorized_user_modify_unowned_observing_run(
    lris, observing_run_token, manage_sources_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    run_id = (
        client(observing_run_token)
        .post_observing_run(ObservingRunPost(**run_details))
        .id
    )

    new_date = {"calendar_date": "2020-02-17"}
    run_details.update(new_date)

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).update_observing_run(
            run_id, ObservingRunUpdate(**new_date)
        )
    assert err.value.status_code == 401


def test_observing_run_assignment_group_names(
    public_assignment,
    public_source,
    view_only_token,
    public_group,
    public_group2,
    upload_data_token_two_groups,
):
    # Save the obj associated with the public_assignment to a group the run
    # owner is not a part of
    client(upload_data_token_two_groups).post_source(
        SourcePost(
            id=public_source.id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group2.id],
        )
    )

    # Get the observing run and associated assignments and check that public_group2
    # is not in the accessible_group_ids
    run = client(view_only_token).fetch_observing_run(public_assignment.run.id)

    assert len(run.assignments) == 1
    assert public_group2.name not in run.assignments[0].accessible_group_names


def test_observing_run_assignment_last_detection(
    public_assignment,
    public_source,
    public_group,
    view_only_token,
    upload_data_token,
    ztf_camera,
):
    """Facilities size exposures from the target's brightness, so the run
    payload carries the last detection alongside each assignment."""
    client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=61254.4,
            instrument_id=ztf_camera.id,
            mag=18.9,
            magerr=0.07,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    run = client(view_only_token).fetch_observing_run(public_assignment.run.id)
    assignment = run.assignments[0]
    assert assignment.last_detected_mag == pytest.approx(18.9, abs=0.01)
    assert assignment.last_detected_filter == "ztfg"
    assert assignment.last_detected_mjd == pytest.approx(61254.4)
