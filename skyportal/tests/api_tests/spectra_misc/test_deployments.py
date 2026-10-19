import skyportal
from skyportal.tests import api


def test_deployments(view_only_token):
    status, data = api("GET", "deployments", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["version"] == skyportal.__version__
    assert data["data"]["deployments"][0]["version"] == skyportal.__version__
    assert data["data"]["system"] is None


def test_deployments_system_info_for_admins(super_admin_token):
    status, data = api("GET", "deployments", token=super_admin_token)
    assert status == 200
    system = data["data"]["system"]
    assert isinstance(system["hostname"], str)
    assert isinstance(system["postgres_version"], str)
