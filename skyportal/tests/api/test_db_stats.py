from skyportal.tests import api


def test_db_stats(view_only_token, public_source, public_group, public_candidate, user):
    status, data = api('GET', 'db_stats', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert isinstance(data['data']['numCandidates'], int)
    assert isinstance(data['data']['numUsers'], int)
    assert isinstance(data['data']['oldestCandidateCreatedAt'], str)
    assert isinstance(data['data']['newestCandidateCreatedAt'], str)
