import base64
import json
import os
import socketserver
import time
import uuid

from tdtax import __version__, taxonomy

from skyportal.tests import api

analysis_port = 6802


def test_post_new_analysis_service(analysis_service_token, public_group):
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:5000/analysis/{name}",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]
    status, data = api(
        "GET", f"analysis_service/{analysis_service_id}", token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"
    for key in post_data:
        if key != "group_ids":
            assert data["data"][key] == post_data[key]
        else:
            assert sorted(g["id"] for g in data["data"]["groups"]) == sorted(
                post_data["group_ids"]
            )

    status, data = api(
        "DELETE",
        f"analysis_service/{analysis_service_id}",
        token=analysis_service_token,
    )
    assert status == 200
    assert data["status"] == "success"


def test_update_analysis_service(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    new_post_data = {"version": "2.0", "timeout": 120.0}

    status, data = api(
        "PATCH",
        f"analysis_service/{analysis_service_id}",
        data=new_post_data,
        token=analysis_service_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"analysis_service/{analysis_service_id}", token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    for key in new_post_data:
        assert data["data"][key] == new_post_data[key]

    status, data = api(
        "DELETE",
        f"analysis_service/{analysis_service_id}",
        token=analysis_service_token,
    )
    assert status == 200
    assert data["status"] == "success"


def test_get_two_analysis_services(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"
    analysis_service_id = data["data"]["id"]

    name_1 = str(uuid.uuid4())
    post_data_1 = {
        "name": name_1,
        "display_name": "another test analysis service name",
        "description": "Another test analysis service description",
        "version": "1.1",
        "contact_name": "Henrietta Swan Leavitt",
        "contact_email": "hsl@harvard.edu",
        "url": f"http://localhost:5000/analysis/{name_1}",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["spectra"],
        "timeout": 1200.0,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data_1, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"
    analysis_service_id_1 = data["data"]["id"]

    status, data = api("GET", "analysis_service", token=analysis_service_token)
    assert status == 200
    assert data["status"] == "success"

    as_ids = [a["id"] for a in data["data"]]
    assert {analysis_service_id, analysis_service_id_1} == set(as_ids)

    for as_id in [analysis_service_id, analysis_service_id_1]:
        status, data = api(
            "DELETE", f"analysis_service/{as_id}", token=analysis_service_token
        )
        assert status == 200
        assert data["status"] == "success"


def test_missing_required_analysis_service_parameter(
    analysis_service_token, public_group
):
    # Do not send `analysis_type` as required

    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "authentication_type": "none",
        "url": f"http://localhost:5000/analysis/{name}",
        "contact_name": "Vera Rubin",
        "input_data_types": ["photometry", "redshift"],
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert "Invalid/missing parameters" in data["message"]


def test_duplicate_analysis_service(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )

    assert status == 200
    assert data["status"] == "success"
    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert "duplicate key value violates unique constraint" in data["message"]

    status, data = api(
        "DELETE",
        f"analysis_service/{analysis_service_id}",
        token=analysis_service_token,
    )
    assert status == 200
    assert data["status"] == "success"


def test_bad_url(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"my_code_{name}.py",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )

    assert status == 400
    assert "a valid `url` is required" in data["message"]


def test_bad_authentication_type(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "oauth2",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )

    assert status == 400
    assert (
        "`authentication_type` must be one of: none, header_token," in data["message"]
    )


def test_authentication_credentials(analysis_service_token, public_group):
    name = str(uuid.uuid4())

    authinfo = {"header_token": {"Authorization": "Bearer MY_TOKEN"}}
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "header_token",
        "_authinfo": json.dumps(authinfo),
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    analysis_service_id = data["data"]["id"]
    status, data = api(
        "GET", f"analysis_service/{analysis_service_id}", token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    # do the credentials match?
    data["data"]["authinfo"] = authinfo

    status, data = api(
        "DELETE",
        f"analysis_service/{analysis_service_id}",
        token=analysis_service_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # Send auth info but for the wrong authentication type
    name = str(uuid.uuid4())
    authinfo = {"header_token": {"Authorization": "Bearer MY_TOKEN"}}
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "api_key",
        "_authinfo": json.dumps(authinfo),
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert """`_authinfo` must contain a key for "api_key".""" in data["message"]


def test_add_and_retrieve_analysis_service_group_access(
    analysis_service_token_two_groups,
    public_group2,
    public_group,
    analysis_service_token,
):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group2.id],
    }

    status, data = api(
        "POST",
        "analysis_service",
        data=post_data,
        token=analysis_service_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"
    analysis_service_id = data["data"]["id"]

    # This token does not belong to public_group2
    status, data = api(
        "GET", f"analysis_service/{analysis_service_id}", token=analysis_service_token
    )
    assert status == 403

    # Both tokens should be able to view this analysis service
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:5000/analysis/{name}",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id, public_group2.id],
    }
    status, data = api(
        "POST",
        "analysis_service",
        data=post_data,
        token=analysis_service_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"
    analysis_service_id = data["data"]["id"]

    status, data = api(
        "GET", f"analysis_service/{analysis_service_id}", token=analysis_service_token
    )
    assert status == 200
    status, data = api(
        "GET",
        f"analysis_service/{analysis_service_id}",
        token=analysis_service_token_two_groups,
    )
    assert status == 200


def test_run_analysis_with_correct_and_incorrect_token(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        # this is the URL/port of the SN analysis service that will be running during testing
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    max_attempts = 20
    analysis_status = "queued"
    params = {"includeAnalysisData": True}

    while max_attempts > 0:
        if analysis_status != "queued":
            break
        status, data = api(
            "GET", f"obj/analysis/{analysis_id}", token=analysis_token, params=params
        )
        assert status == 200
        assert data["data"]["analysis_service_id"] == analysis_service_id
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(5)
    else:
        assert False, (
            f"analysis was not started properly ({data['data']['status_message']})"
        )

    # Since this is random data, this fit might succeed (usually) or fail (seldom)
    # that's ok because it means we're getting the
    # roundtrip return of the webhhook
    if analysis_status == "success":
        assert set(data["data"]["data"].keys()) == {
            "inference_data",
            "plots",
            "results",
        }

    # try to start an analysis with the wrong token access
    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_service_token,
    )
    assert status == 401


def test_run_analysis_with_bad_inputs(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    # bad analysis service id
    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/999999999",
        token=analysis_token,
    )
    assert status == 403
    assert data["message"].find("Could not access Analysis Service") != -1

    # bad obj id
    status, data = api(
        "POST",
        f"obj/badObjectName1/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 404
    assert data["message"].find("not found") != -1

    # bad resource type. This route does not exist.
    status, data = api(
        "POST",
        f"candidate/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 405


def test_run_analysis_with_down_and_wrong_analysis_service(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    # get an unused port on localhost
    with socketserver.TCPServer(("localhost", 0), None) as s:
        unused_port = s.server_address[1]

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{unused_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    # this should still go through but the analysis
    # itself should not work because we're sending this off
    # to a service that does not exist
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    max_attempts = 20
    analysis_status = "queued"

    while max_attempts > 0:
        if analysis_status != "queued":
            break
        status, data = api("GET", f"obj/analysis/{analysis_id}", token=analysis_token)
        assert status == 200
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(5)

    assert analysis_status == "failure"

    # now try a bad endpoint
    name_bad_endpoint = str(uuid.uuid4())

    post_data = {
        "name": name_bad_endpoint,
        "display_name": "a bad endpoint test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{analysis_port}/analysis/bad_endpoint_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    # this should still go through but the analysis
    # itself should not work
    assert status == 200
    assert data["status"] == "success"

    max_attempts = 5
    analysis_status = "queued"

    while max_attempts > 0:
        if analysis_status != "queued":
            break
        status, data = api("GET", f"obj/analysis/{analysis_id}", token=analysis_token)
        assert status == 200
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(1)

    assert analysis_status == "failure"


def test_delete_analysis(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    status, data = api(
        "DELETE",
        f"obj/analysis/{analysis_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"


def test_delete_analysis_service_cascades_to_delete_associated_analysis(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    # wait until the analysis is done
    max_attempts = 20
    analysis_status = "queued"
    while max_attempts > 0:
        if analysis_status != "queued":
            break
        status, data = api("GET", f"obj/analysis/{analysis_id}", token=analysis_token)
        assert status == 200
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(5)

    # get the analysis associated with the
    # analysis service
    params = {"includeFilename": True}
    status, data = api(
        "GET",
        f"obj/analysis/{analysis_id}",
        token=analysis_token,
        params=params,
    )
    assert status == 200
    if analysis_status == "completed":
        # there should be a filename if the analysis succeeded
        filename = data["data"]["filename"]
        assert os.path.exists(filename)

    # delete the analysis service...
    status, data = api(
        "DELETE",
        f"analysis_service/{analysis_service_id}",
        token=analysis_service_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # now to try get the analysis associated with the
    # deleted analysis service
    status, data = api(
        "GET",
        f"obj/analysis/{analysis_id}",
        token=analysis_token,
    )
    assert status == 403
    assert data["status"] == "error"
    if analysis_status == "completed":
        # this file should be removed if it was
        # created when the analysis service completed
        assert not os.path.exists(filename)


def test_retrieve_data_products(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())
    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}
    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        # this is the URL/port of the SN analysis service that will be running during testing
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    max_attempts = 20
    analysis_status = "queued"

    while max_attempts > 0:
        if analysis_status not in ["queued", "pending"]:
            break
        status, data = api(
            "GET",
            f"obj/analysis/{analysis_id}",
            token=analysis_token,
        )
        assert status == 200
        assert data["data"]["analysis_service_id"] == analysis_service_id
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(3)
    else:
        assert False, (
            f"analysis was not started properly ({data['data']['status_message']})"
        )

    if analysis_status == "completed":
        # try to get a plot
        response = api(
            "GET",
            f"obj/analysis/{analysis_id}/plots/0",
            token=analysis_token,
            raw_response=True,
        )
        status = response.status_code
        data = response.text
        assert status == 200
        assert isinstance(data, str)
        assert data[0:10].find("PNG") != -1
        assert response.headers.get("Content-Type", "Empty").find("image/png") != -1

        # try to get a plot which should not be there
        response = api(
            "GET",
            f"obj/analysis/{analysis_id}/plots/99999",
            token=analysis_token,
            raw_response=True,
        )
        status = response.status_code
        data = response.text
        assert status == 404

        # try to get the corner plot of the posterior
        response = api(
            "GET",
            f"obj/analysis/{analysis_id}/corner",
            token=analysis_token,
            raw_response=True,
        )
        status = response.status_code
        data = response.text
        assert status == 200
        assert isinstance(data, str)
        assert data[0:10].find("PNG") != -1
        assert response.headers.get("Content-Type", "Empty").find("image/png") != -1

        # try to get the results
        status, data = api(
            "GET",
            f"obj/analysis/{analysis_id}/results",
            token=analysis_token,
        )
        assert status == 200
        assert data["status"] == "success"
        assert isinstance(data["data"], dict)
    else:
        # try to get a plot which does not exist
        response = api(
            "GET",
            f"obj/analysis/{analysis_id}/plots/0",
            token=analysis_token,
            raw_response=True,
        )
        status = response.status_code
        data = response.text
        assert status == 404

        # try to get a corner plot which does not exist
        response = api(
            "GET",
            f"obj/analysis/{analysis_id}/corner",
            token=analysis_token,
            raw_response=True,
        )
        status = response.status_code
        data = response.text
        assert status == 404
        assert data.find("No data found") != -1

        # try to get a non-existing results
        status, data = api(
            "GET",
            f"obj/analysis/{analysis_id}/results",
            token=analysis_token,
        )
        assert status == 404
        assert data["message"].find("No data found") != -1


def test_upload_analysis(
    analysis_service_token, analysis_token, public_group, public_source, view_only_token
):
    name = str(uuid.uuid4())

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vesto Slipher",
        "contact_email": "vs@ls.st",
        "url": "http://example.com",
        "authentication_type": "none",
        "analysis_type": "meta_analysis",
        "upload_only": True,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    # this should fail because the analysis service is an upload_only service
    # and the normal analysis endpoint (which kicks off a webhook) is
    # not allowed.
    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 403
    assert data["message"].find("analysis_upload endpoint") != -1

    # this should succeed as the correct endpoint is being used for an
    # upload_only service
    params = {
        "show_parameters": True,
        "analysis": {
            "results": {
                "format": "json",
                "data": {"external_provenance_id": str(uuid.uuid4())},
            }
        },
    }
    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis_upload/{analysis_service_id}",
        token=analysis_token,
        data=params,
    )
    assert status == 200
    assert data["status"] == "success"

    # this should succeed but we should be warned that we didn't
    # provide any analysis results
    params = {"show_parameters": True}
    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis_upload/{analysis_service_id}",
        token=analysis_token,
        data=params,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["message"].find("empty analysis upload_only results") != -1

    # this should fail because the user's token does not have "Run Analyses"
    # persmissions
    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis_upload/{analysis_service_id}",
        token=view_only_token,
        data=params,
    )
    assert status == 401


def test_run_analysis_with_file_input(
    analysis_service_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    optional_analysis_parameters = {
        "image_data": {"type": "file", "required": "True", "description": "Image data"},
        "fluxcal_data": {"type": "file", "description": "Fluxcal data"},
        "centroid_X": {"type": "number"},
        "centroid_Y": {"type": "number"},
        "spaxel_buffer": {"type": "number"},
    }

    post_data = {
        "name": name,
        "display_name": "Spectral_Cube_Analysis",
        "description": "Spectral_Cube_Analysis description",
        "version": "1.0",
        "contact_name": "Michael Coughlin",
        # this is the URL/port of the Spectral_Cube_Analysis service that will be running during testing
        "url": "http://localhost:7003/analysis/spectral_cube_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "spectrum_fitting",
        "input_data_types": [],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    datafile = f"{os.path.dirname(__file__)}/../data/spectral_cube_analysis.fits"
    with open(datafile, "rb") as fid:
        payload = fid.read()

    payload = f"data:image/fits;name=spectral_cube_analysis.fits;base64,{base64.b64encode(payload).decode('utf-8')}"

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
        data={
            "show_parameters": True,
            "show_plots": True,
            "show_corner": True,
            "analysis_parameters": {"image_data": payload},
        },
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    max_attempts = 20
    analysis_status = "queued"
    params = {"includeAnalysisData": True}

    while max_attempts > 0:
        if analysis_status != "queued":
            break
        status, data = api(
            "GET", f"obj/analysis/{analysis_id}", token=analysis_token, params=params
        )
        assert status == 200
        assert data["data"]["analysis_service_id"] == analysis_service_id
        analysis_status = data["data"]["status"]

        max_attempts -= 1
        time.sleep(5)
    else:
        assert False, (
            f"analysis was not started properly ({data['data']['status_message']})"
        )


def test_default_analysis(
    analysis_service_token,
    analysis_token,
    public_group,
    public_source,
    taxonomy_token,
    classification_token,
):
    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": taxonomy_name,
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    post_data = {
        "name": name,
        "display_name": "test default analysis service name",
        "description": "A test default analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        # this is the URL/port of the SN analysis service that will be running during testing
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "optional_analysis_parameters": json.dumps(optional_analysis_parameters),
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    data = {
        "default_analysis_parameters": {
            "test_parameters": "test_value_1",
        },
        "group_ids": [public_group.id],
        "source_filter": {"classifications": [{"name": "Algol", "probability": 0.5}]},
        "daily_limit": 1,
    }

    url = f"analysis_service/{analysis_service_id}/default_analysis"

    status, data = api(
        "POST",
        url,
        data=data,
        token=analysis_token,
    )

    assert status == 200
    assert data["status"] == "success"
    default_analysis_id = data["data"]["id"]

    # insert a classification which probability is too low to trigger the default analysis
    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 0.4,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    n_retries = 0
    while n_retries < 10:
        status, data = api(
            "GET",
            "obj/analysis",
            params={
                "objID": public_source.id,
                "analysisServiceID": analysis_service_id,
            },
            token=analysis_token,
        )
        if len(data["data"]) == 1:
            assert False
        else:
            time.sleep(1)
            n_retries += 1

    # insert a classification which probability is high enough to trigger the default analysis
    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 0.9,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    n_retries = 0
    while n_retries < 20:
        status, data = api(
            "GET",
            "obj/analysis",
            params={
                "objID": public_source.id,
                "analysisServiceID": analysis_service_id,
            },
            token=analysis_token,
        )
        if status == 200 and data["status"] == "success" and len(data["data"]) == 1:
            break
        else:
            time.sleep(1)
            n_retries += 1

    assert n_retries < 20

    # verify that the daily limit is respected, i.e. that the default analysis is not run again
    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": public_source.id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 0.9,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    n_retries = 0
    while n_retries < 10:
        status, data = api(
            "GET",
            "obj/analysis",
            params={
                "objID": public_source.id,
                "analysisServiceID": analysis_service_id,
            },
            token=analysis_token,
        )
        if len(data["data"]) == 2:
            assert False
        else:
            time.sleep(1)
            n_retries += 1

    status, data = api(
        "DELETE",
        f"{url}/{default_analysis_id}",
        token=analysis_token,
    )
    assert status == 200


def test_source_analysis(
    analysis_service_token, view_only_token, analysis_token, public_group, public_source
):
    name = str(uuid.uuid4())

    post_data = {
        "name": name,
        "display_name": "test analysis service name",
        "description": "A test analysis service description",
        "version": "1.0",
        "contact_name": "Vera Rubin",
        "contact_email": "vr@ls.st",
        "url": f"http://localhost:{analysis_port}/analysis/demo_analysis",
        "authentication_type": "none",
        "analysis_type": "lightcurve_fitting",
        "input_data_types": ["photometry", "redshift"],
        "timeout": 60,
        "group_ids": [public_group.id],
    }

    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_service_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"obj/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 200
    assert data["status"] == "success"

    analysis_id = data["data"].get("id")
    assert analysis_id is not None

    params = {"includeAnalyses": True}
    status, data = api(
        "GET", f"sources/{public_source.id}", token=view_only_token, params=params
    )
    assert status == 200
    assert data["status"] == "success"
    assert "analyses" in data["data"]
    assert any(analysis["id"] == analysis_id for analysis in data["data"]["analyses"])
