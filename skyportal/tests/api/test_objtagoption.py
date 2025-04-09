import random

from skyportal.tests import api


def test_add_tag(super_admin_token):
    data = {"tag_name": f"test_tag_{random.randint(0,100000)}"}
    status, data = api("POST", "objtagoption", data=data, token=super_admin_token)
    assert status == 200

def test_get_tags(super_admin_token):
    status, data = api("GET", "objtagoption", token=super_admin_token)
    assert status == 200
    
def test_delete_tag(super_admin_token):
    status, data = api("DELETE", "objtagoption/3", token=super_admin_token)
    assert status == 200

def test_modify_tag(super_admin_token):
    data = {"tag_name": f"tag_renamed_{random.randint(0,100000)}"}
    status, data = api("PUT", "objtagoption/2", data=data, token=super_admin_token)
    assert status == 200