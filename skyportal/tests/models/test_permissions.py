import pytest
from skyportal.models import Base, Candidate

subclasses = Base.__subclasses__()
access_types = ['create', 'read', 'update', 'delete']
parameters = [(c, m) for c in subclasses for m in access_types]


check_all_access_modes = pytest.mark.parametrize("mode", access_types)


@check_all_access_modes
def test_candidate_super_admin_user_can_view(
    mode, super_admin_user, public_candidate, public_candidate_two_groups
):
    # load a record into the DB
    cand1 = public_candidate.candidates[0]
    cand2 = public_candidate_two_groups.candidates[0]
    results = Candidate.get_records_accessible_by(super_admin_user, mode=mode)
    assert cand1 in results
    assert cand2 in results
    for instance in results:
        accessible = instance.is_accessible_by(super_admin_user, mode=mode)
        assert accessible


@check_all_access_modes
def test_candidate_is_blocked_from_cross_group_access(
    mode, user_group2, public_candidate
):
    # load a record into the DB
    candidate = public_candidate.candidates[0]
    accessible = candidate.is_accessible_by(user_group2, mode=mode)
    assert not accessible


@check_all_access_modes
def test_regular_group_user_can_control_candidate(mode, user, public_candidate):
    cand = public_candidate.candidates[0]
    assert cand.is_accessible_by(user, mode=mode)
