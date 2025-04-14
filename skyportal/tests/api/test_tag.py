import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from skyportal.models import ObjTagOption
from skyportal.tests import api


# --- Testing ObjTagOption API
def test_get_tag(super_admin_token):
    tag_to_create = {"tag_name": f"test_get_{random.randint(0,100000)}"}
    status, created_tag = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)

    tag_name = created_tag['data']['tag_name']
    tag_id = created_tag['data']['id']

    status_by_id, _ = api("GET", f"objtagoption/{tag_id}", token=super_admin_token)
    assert status_by_id == 200

    status_by_id, _ = api("GET", f"objtagoption/999999", token=super_admin_token)
    assert status_by_id == 404

    status_by_name, _ = api("GET", f"objtagoption/bonjour", token=super_admin_token)
    assert status_by_name == 404 

    status, _ = api("GET", "objtagoption", token=super_admin_token)
    assert status == 200
    
def test_add_tag(super_admin_token):
    tag_to_create = {"tag_name": f"tag_added_{random.randint(0,100000)}"}
    status, created_tag = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 200

    # Verification that the tag exists
    tag_id = created_tag['data']['id']
    verify_status, _ = api("GET", f"objtagoption/{tag_id}", token=super_admin_token)
    assert verify_status == 200 

    # Verification that we can't create the same tag twice
    status, created_tag = api("POST", "objtagoption", data=tag_to_create, token=super_admin_token)
    assert status == 404

    # Verification that we can't create a tag without a name
    status, created_tag = api("POST", "objtagoption", data="", token=super_admin_token)
    assert status == 500

def test_modify_tag(super_admin_token):
    # Creation of a tag to modify
    tag_data = {"tag_name": f"tag_to_modify_{random.randint(0,100000)}"}
    create_status, created_tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert create_status == 200

    tag_id = created_tag['data']['id']
    data = {"tag_name": f"tag_renamed_{random.randint(0,100000)}"}

    # Testing nominal case
    status, data = api("PUT", f"objtagoption/{tag_id}", data=data, token=super_admin_token)
    assert status == 200

    # Testing to rename a tag with an existing name
    status, data = api("PUT", f"objtagoption/{tag_id}", data=data, token=super_admin_token)
    assert status == 400

    # Testing to rename a tag without tag_name
    status, data = api("PUT", f"objtagoption/{tag_id}", data="", token=super_admin_token)
    assert status == 500

    # Testing to rename a non existing tag
    data = {"tag_name": f"tag_not_found_{random.randint(0,100000)}"}
    status, data = api("PUT", f"objtagoption/9999999", data=data, token=super_admin_token)
    assert status == 404

def test_delete_tag(super_admin_token):
    # Creation of a tag to delete
    tag_data = {"tag_name": f"tag_to_delete_{random.randint(0,100000)}"}
    create_status, created_tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    assert create_status == 200
    tag_id = created_tag['data']['id']
    
    # Delete the tag
    delete_status, _ = api("DELETE", f"objtagoption/{tag_id}", token=super_admin_token)
    assert delete_status == 200
    
    # Verification that the tag does not exist anymore
    verify_status, verify_tag = api("GET", f"objtagoption/{tag_id}", token=super_admin_token)
    assert verify_status == 404

    # Verification that we can't delete a tag that doesn't exist
    delete_status, _ = api("DELETE", f"objtagoption/{tag_id}", token=super_admin_token)
    assert delete_status == 404

# --- Testing ObjTag API
def test_create_tag_source_association(super_admin_token):
    # Create a tag option
    tag_data = {"tag_name": f"tag_{random.randint(0,100000)}"}
    _, tag = api("POST", "objtagoption", data=tag_data, token=super_admin_token)
    
    assoc_data = {
        "objtagoption_id": tag['data']['id'],
        "source_id": 1 # Associate it to the first source of the demo data
    }
    
    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 200
    
    status, data = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    assert status == 400
    assert "already exists" in data['message']

def test_update_association(super_admin_token):
    # Create two tags options
    tag1_data = {"tag_name": f"tag1_{random.randint(0,100000)}"}
    _, tag1 = api("POST", "objtagoption", data=tag1_data, token=super_admin_token)
    
    tag2_data = {"tag_name": f"tag2_{random.randint(0,100000)}"}
    _, tag2 = api("POST", "objtagoption", data=tag2_data, token=super_admin_token)
    
    assoc_data = {
        "objtagoption_id": tag1['data']['id'],
        "source_id": 1
    }
    _, assoc = api("POST", "objtag", data=assoc_data, token=super_admin_token)
    
    # Testing nominal case
    update_data = {"objtagoption_id": tag2['data']['id']}
    status, _ = api(
        "PUT", 
        f"objtag/{assoc['data']['id']}", 
        data=update_data, 
        token=super_admin_token
    )
    assert status == 200

    # Testing to modify an association with a non exisiting tag id
    update_data = {"objtagoption_id": 9999999}
    status, data = api(
        "PUT", 
        f"objtag/{assoc['data']['id']}", 
        data=update_data, 
        token=super_admin_token
    )
    assert status == 404
    assert "Specified tag does not exist" in data['message']


    # Testing to modify a non existing association
    update_data = {"objtagoption_id": tag2['data']['id']}
    status, data = api(
        "PUT", 
        f"objtag/999999999", 
        data=update_data, 
        token=super_admin_token
    )
    assert status == 404
    assert "Association not found" in data['message']

    #  Testing to modify an association with a non exisiting source id
    update_data = {"source_id": 999999}
    status, data = api(
        "PUT", 
        f"objtag/{assoc['data']['id']}", 
        data=update_data, 
        token=super_admin_token
    )
    assert status == 404
    assert "Specified source does not exist" in data['message']

    # Testing association of the same tag twice to a source
    update_data = {"source_id": 1}
    status, data = api(
        "PUT", 
        f"objtag/{assoc['data']['id']}", 
        data=update_data, 
        token=super_admin_token
    )
    assert status == 409
    assert "already exists" in data['message']



def test_delete_association(super_admin_token):
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

    status, _ = api(
            "DELETE", 
            f"objtag/{assoc['data']['id']}", 
            token=super_admin_token
        )
    assert status == 404
