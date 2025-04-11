import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from skyportal.models import ObjTagOption
from skyportal.tests import api


def test_add_tag(super_admin_token):
    tag_to_create = {"tag_name": f"tag_added_{random.randint(0,100000)}"}
    status, created_tag = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 200

    # tag_id = created_tag['data']['id']
    # verify_status, _ = api("GET", f"objtagoption/{tag_id}", token=super_admin_token)
    # assert verify_status == 200 

def test_get_tags(super_admin_token):
    tag_to_create = {"tag_name": f"tag_get_{random.randint(0,100000)}"}
    status, created_tag = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)

    # print(f">>> {created_tag}")
    # tag_name = created_tag['data']['tag_name']

    # tag_id = created_tag['data']['id']

    # status_by_id, c = api("GET", f"objtagoption/{tag_id}", token=super_admin_token)
    # assert status_by_id == 200 
    # print(f">>> C {c}")

    # status_by_name, a = api("GET", f"objtagoption/{tag_name}", token=super_admin_token)
    # assert status_by_name == 200 
    # print(f">>> A {a}")

    status, b = api("GET", "objtagoption", token=super_admin_token)
    assert status == 200
    print(f">>> B {b}")

def test_modify_tag(super_admin_token):
    # Creation of a tag to modify
    tag_data = {"tag_name": f"tag_to_modify_{random.randint(0,100000)}"}
    create_status, created_tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert create_status == 200

    tag_id = created_tag['data']['id']

    data = {"tag_name": f"tag_renamed_{random.randint(0,100000)}"}
    status, data = api("PUT", f"objtagoption/{tag_id}", data=data, token=super_admin_token)
    assert status == 200

def test_delete_tag(super_admin_token):
    # Creation of a tag to delete
    tag_data = {"tag_name": f"tag_to_delete_{random.randint(0,100000)}"}
    create_status, created_tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert create_status == 200
    tag_id = created_tag['data']['id']
    
    delete_status, _ = api("DELETE", f"objtagoption/{tag_id}", token=super_admin_token)
    assert delete_status == 200
    
    # Verification that the tag does not exist anymore
    verify_status, verify_tag = api("GET", f"objtagoption/{tag_id}", token=super_admin_token)
    assert verify_status == 404

def test_create_tag_source_association(super_admin_token):
    """Testing POST request : associate a tag to a source"""
    tag_data = {"tag_name": f"tag_{random.randint(0,100000)}"}
    _, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    
    assoc_data = {
        "objtagoption_id": tag['data']['id'],
        "source_id": 1
    }
    
    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200
    
    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 400
    assert "already exists" in data['message']

def test_update_association(super_admin_token):
    tag1_data = {"tag_name": f"tag1_{random.randint(0,100000)}"}
    _, tag1 = api("POST", "objtagoption", data=tag1_data, token=super_admin_token)
    
    tag2_data = {"tag_name": f"tag2_{random.randint(0,100000)}"}
    _, tag2 = api("POST", "objtagoption", data=tag2_data, token=super_admin_token)
    
    assoc_data = {
        "objtagoption_id": tag1['data']['id'],
        "source_id": 1
    }
    _, assoc = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    
    update_data = {"objtagoption_id": tag2['data']['id']}
    status, _ = api(
        "PUT", 
        f"objtag/{assoc['data']['id']}", 
        data=update_data, 
        token=super_admin_token
    )
    assert status == 200


def test_delete_association(super_admin_token):
    """Test suppression d'une association"""
    tag_data = {"tag_name": f"tag_delete_association_{random.randint(0,100000)}"}
    _, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    
    assoc_data = {
        "objtagoption_id": tag['data']['id'],
        "source_id": 1
    }
    _, assoc = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    
    status, _ = api(
        "DELETE", 
        f"objtag/{assoc['data']['id']}", 
        token=super_admin_token
    )
    assert status == 200