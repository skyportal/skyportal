import base64
import json
import os
import socketserver
import time
import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.analysis import (
    AnalysisPost,
    AnalysisServicePost,
    AnalysisServiceUpdate,
    AnalysisUploadPost,
    DefaultAnalysisPost,
)
from skyportal_py.classifications import ClassificationPost
from skyportal_py.sources import SourcePost
from skyportal_py.taxonomies import TaxonomyPost
from tdtax import __version__, taxonomy

from skyportal.tests import api, client, retry_until

analysis_port = 6802


def test_post_new_analysis_service(analysis_service_token, public_group):
    sp = client(analysis_service_token)
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    analysis_service_id = sp.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    service = sp.fetch_analysis_service(analysis_service_id)
    assert service.name == name
    assert service.display_name == "test analysis service name"
    assert service.description == "A test analysis service description"
    assert service.version == "1.0"
    assert service.contact_name == "Vera Rubin"
    assert service.contact_email == "vr@ls.st"
    assert service.url == f"http://localhost:5000/analysis/{name}"
    assert service.optional_analysis_parameters == json.dumps(
        optional_analysis_parameters
    )
    assert service.authentication_type == "none"
    assert service.analysis_type == "lightcurve_fitting"
    assert service.input_data_types == ["photometry", "redshift"]
    assert service.timeout == 60
    assert sorted(g.id for g in service.groups) == sorted([public_group.id])

    sp.delete_analysis_service(analysis_service_id)


def test_update_analysis_service(analysis_service_token, public_group):
    sp = client(analysis_service_token)
    name = str(uuid.uuid4())
    analysis_service_id = sp.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    sp.update_analysis_service(
        analysis_service_id, AnalysisServiceUpdate(version="2.0", timeout=120.0)
    )

    service = sp.fetch_analysis_service(analysis_service_id)
    assert service.version == "2.0"
    assert service.timeout == 120.0

    sp.delete_analysis_service(analysis_service_id)


def test_update_analysis_service_groups(super_admin_token, public_group, public_group2):
    # Super admin, so the group-membership check passes and we reach the
    # groups reassignment (the fixed code path).
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    analysis_service_id = sp.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    # Reassigning groups on an existing service must not raise the async
    # greenlet_spawn error from lazy-loading the old groups collection to diff it.
    sp.update_analysis_service(
        analysis_service_id,
        AnalysisServiceUpdate(group_ids=[public_group.id, public_group2.id]),
    )

    service = sp.fetch_analysis_service(analysis_service_id)
    assert sorted(g.id for g in service.groups) == sorted(
        [public_group.id, public_group2.id]
    )

    sp.delete_analysis_service(analysis_service_id)


def test_update_default_analysis(super_admin_token, public_group, public_group2):
    # Super admin so the group-membership check passes for both groups.
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    optional_analysis_parameters = {"first": ["a", "b"], "second": ["x"]}
    analysis_service_id = sp.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test default analysis update",
            description="A test default analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    default_analysis_id = sp.post_default_analysis(
        analysis_service_id,
        DefaultAnalysisPost(
            default_analysis_parameters={"first": "a"},
            source_filter={"group_id": public_group.id},
            daily_limit=1,
            group_ids=[public_group.id],
        ),
    ).id

    # Partial update: change params + source_filter + reassign groups (the group
    # reassignment is the lazy-load path that must not raise greenlet_spawn).
    sp.update_default_analysis(
        analysis_service_id,
        default_analysis_id,
        DefaultAnalysisPost(
            default_analysis_parameters={"first": "b", "second": "x"},
            source_filter={"group_id": public_group2.id},
            daily_limit=5,
            group_ids=[public_group.id, public_group2.id],
        ),
    )

    d = sp.fetch_default_analysis(analysis_service_id, default_analysis_id)
    assert d.default_analysis_parameters == {"first": "b", "second": "x"}
    assert d.source_filter == {"group_id": public_group2.id}
    assert sorted(g.id for g in d.groups) == sorted([public_group.id, public_group2.id])

    # A param key not declared in optional_analysis_parameters is rejected.
    with pytest.raises(SkyPortalError) as err:
        sp.update_default_analysis(
            analysis_service_id,
            default_analysis_id,
            DefaultAnalysisPost(default_analysis_parameters={"undeclared_key": "z"}),
        )
    assert err.value.status_code == 400

    sp.delete_default_analysis(analysis_service_id, default_analysis_id)


def test_get_two_analysis_services(analysis_service_token, public_group):
    sp = client(analysis_service_token)
    name = str(uuid.uuid4())
    analysis_service_id = sp.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    name_1 = str(uuid.uuid4())
    analysis_service_id_1 = sp.post_analysis_service(
        AnalysisServicePost(
            name=name_1,
            display_name="another test analysis service name",
            description="Another test analysis service description",
            version="1.1",
            contact_name="Henrietta Swan Leavitt",
            contact_email="hsl@harvard.edu",
            url=f"http://localhost:5000/analysis/{name_1}",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["spectra"],
            timeout=1200.0,
            group_ids=[public_group.id],
        )
    ).id

    as_ids = [a.id for a in sp.fetch_analysis_services()]
    assert {analysis_service_id, analysis_service_id_1} == set(as_ids)

    for as_id in [analysis_service_id, analysis_service_id_1]:
        sp.delete_analysis_service(as_id)


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

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )
    assert status == 400
    assert "Invalid/missing parameters" in data["message"]


def test_duplicate_analysis_service(analysis_service_token, public_group):
    sp = client(analysis_service_token)
    name = str(uuid.uuid4())
    payload = AnalysisServicePost(
        name=name,
        display_name="test analysis service name",
        description="A test analysis service description",
        version="1.0",
        contact_name="Vera Rubin",
        url=f"http://localhost:5000/analysis/{name}",
        authentication_type="none",
        analysis_type="lightcurve_fitting",
        input_data_types=["photometry", "redshift"],
        group_ids=[public_group.id],
    )

    analysis_service_id = sp.post_analysis_service(payload).id

    with pytest.raises(
        SkyPortalError, match="duplicate key value violates unique constraint"
    ) as err:
        sp.post_analysis_service(payload)
    assert err.value.status_code == 400

    sp.delete_analysis_service(analysis_service_id)


def test_bad_url(analysis_service_token, public_group):
    name = str(uuid.uuid4())
    with pytest.raises(SkyPortalError, match="a valid `url` is required") as err:
        client(analysis_service_token).post_analysis_service(
            AnalysisServicePost(
                name=name,
                display_name="test analysis service name",
                description="A test analysis service description",
                version="1.0",
                contact_name="Vera Rubin",
                url=f"my_code_{name}.py",
                authentication_type="none",
                analysis_type="lightcurve_fitting",
                input_data_types=["photometry", "redshift"],
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400


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

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST", "analysis_service", data=post_data, token=analysis_service_token
    )

    assert status == 400
    assert (
        "`authentication_type` must be one of: none, header_token," in data["message"]
    )


def test_authentication_credentials(analysis_service_token, public_group):
    sp = client(analysis_service_token)
    name = str(uuid.uuid4())

    authinfo = {"header_token": {"Authorization": "Bearer MY_TOKEN"}}
    analysis_service_id = sp.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            url=f"http://localhost:5000/analysis/{name}",
            authentication_type="header_token",
            authinfo=json.dumps(authinfo),
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            group_ids=[public_group.id],
        )
    ).id
    sp.fetch_analysis_service(analysis_service_id)

    # do the credentials match?
    # (the original test only reassigned the response dict here; no assertion)

    sp.delete_analysis_service(analysis_service_id)

    # Send auth info but for the wrong authentication type
    name = str(uuid.uuid4())
    authinfo = {"header_token": {"Authorization": "Bearer MY_TOKEN"}}
    with pytest.raises(
        SkyPortalError, match='`_authinfo` must contain a key for "api_key"'
    ) as err:
        sp.post_analysis_service(
            AnalysisServicePost(
                name=name,
                display_name="test analysis service name",
                description="A test analysis service description",
                version="1.0",
                contact_name="Vera Rubin",
                url=f"http://localhost:5000/analysis/{name}",
                authentication_type="api_key",
                authinfo=json.dumps(authinfo),
                analysis_type="lightcurve_fitting",
                input_data_types=["photometry", "redshift"],
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400


def test_add_and_retrieve_analysis_service_group_access(
    analysis_service_token_two_groups,
    public_group2,
    public_group,
    analysis_service_token,
):
    sp_two_groups = client(analysis_service_token_two_groups)
    sp = client(analysis_service_token)
    name = str(uuid.uuid4())
    analysis_service_id = sp_two_groups.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group2.id],
        )
    ).id

    # This token does not belong to public_group2
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_analysis_service(analysis_service_id)
    assert err.value.status_code == 403

    # Both tokens should be able to view this analysis service
    name = str(uuid.uuid4())
    analysis_service_id = sp_two_groups.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:5000/analysis/{name}",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id, public_group2.id],
        )
    ).id

    sp.fetch_analysis_service(analysis_service_id)
    sp_two_groups.fetch_analysis_service(analysis_service_id)


def test_run_analysis_with_correct_and_incorrect_token(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            # this is the URL/port of the SN analysis service that will be running during testing
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    analysis_id = sp_analysis.post_analysis(public_source.id, analysis_service_id).id
    assert analysis_id is not None

    def analysis_started():
        analysis = sp_analysis.fetch_analysis(analysis_id, include_analysis_data=True)
        assert analysis.analysis_service_id == analysis_service_id
        assert analysis.status != "queued", (
            f"analysis was not started properly ({analysis.status_message})"
        )
        return analysis

    analysis = retry_until(analysis_started, timeout=100)
    analysis_status = analysis.status

    # Since this is random data, this fit might succeed (usually) or fail (seldom)
    # that's ok because it means we're getting the
    # roundtrip return of the webhhook
    if analysis_status == "success":
        assert set(analysis.data.keys()) == {
            "inference_data",
            "plots",
            "results",
        }

    # try to start an analysis with the wrong token access
    with pytest.raises(SkyPortalError) as err:
        sp_service.post_analysis(public_source.id, analysis_service_id)
    assert err.value.status_code == 401


def test_run_analysis_with_bad_inputs(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    # bad analysis service id
    with pytest.raises(
        SkyPortalError, match="Could not access Analysis Service"
    ) as err:
        sp_analysis.post_analysis(public_source.id, 999999999)
    assert err.value.status_code == 403

    # bad obj id
    with pytest.raises(SkyPortalError, match="not found") as err:
        sp_analysis.post_analysis("badObjectName1", analysis_service_id)
    assert err.value.status_code == 404

    # bad resource type. This route does not exist.
    # raw api: nonexistent route the typed client can't produce
    status, data = api(
        "POST",
        f"candidate/{public_source.id}/analysis/{analysis_service_id}",
        token=analysis_token,
    )
    assert status == 405


def test_run_analysis_with_down_and_wrong_analysis_service(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    # get an unused port on localhost
    with socketserver.TCPServer(("localhost", 0), None) as s:
        unused_port = s.server_address[1]

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{unused_port}/analysis/demo_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    # this should still go through but the analysis
    # itself should not work because we're sending this off
    # to a service that does not exist
    analysis_id = sp_analysis.post_analysis(public_source.id, analysis_service_id).id
    assert analysis_id is not None

    def analysis_done():
        analysis = sp_analysis.fetch_analysis(analysis_id)
        assert analysis.status != "queued"
        return analysis.status

    assert retry_until(analysis_done, timeout=100) == "failure"

    # now try a bad endpoint
    name_bad_endpoint = str(uuid.uuid4())

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name_bad_endpoint,
            display_name="a bad endpoint test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/bad_endpoint_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    # this should still go through but the analysis
    # itself should not work
    sp_analysis.post_analysis(public_source.id, analysis_service_id)

    assert retry_until(analysis_done, timeout=10) == "failure"


def test_delete_analysis(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    analysis_id = sp_analysis.post_analysis(public_source.id, analysis_service_id).id
    assert analysis_id is not None

    sp_analysis.delete_analysis(analysis_id)


def test_delete_analysis_service_cascades_to_delete_associated_analysis(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    analysis_id = sp_analysis.post_analysis(public_source.id, analysis_service_id).id
    assert analysis_id is not None

    def analysis_done():
        analysis = sp_analysis.fetch_analysis(analysis_id)
        assert analysis.status != "queued"
        return analysis.status

    analysis_status = retry_until(analysis_done, timeout=100)

    # get the analysis associated with the
    # analysis service
    analysis = sp_analysis.fetch_analysis(analysis_id, include_filename=True)
    if analysis_status == "completed":
        # there should be a filename if the analysis succeeded
        filename = analysis.filename
        assert os.path.exists(filename)

    # delete the analysis service...
    sp_service.delete_analysis_service(analysis_service_id)

    # now to try get the analysis associated with the
    # deleted analysis service
    with pytest.raises(SkyPortalError) as err:
        sp_analysis.fetch_analysis(analysis_id)
    assert err.value.status_code == 403
    if analysis_status == "completed":
        # this file should be removed if it was
        # created when the analysis service completed
        assert not os.path.exists(filename)


def test_retrieve_data_products(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())
    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}
    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            # this is the URL/port of the SN analysis service that will be running during testing
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    analysis_id = sp_analysis.post_analysis(public_source.id, analysis_service_id).id
    assert analysis_id is not None

    def analysis_started():
        analysis = sp_analysis.fetch_analysis(analysis_id)
        assert analysis.analysis_service_id == analysis_service_id
        assert analysis.status not in ["queued", "pending"], (
            f"analysis was not started properly ({analysis.status_message})"
        )
        return analysis.status

    analysis_status = retry_until(analysis_started, timeout=60)

    if analysis_status == "completed":
        # try to get a plot
        # raw api: response-header assertion the typed client would mask
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
        with pytest.raises(SkyPortalError) as err:
            sp_analysis.fetch_analysis_plot(analysis_id, plot_number=99999)
        assert err.value.status_code == 404

        # try to get the results
        results = sp_analysis.fetch_analysis_results(analysis_id)
        assert isinstance(results, dict)
    else:
        # try to get a plot which does not exist
        with pytest.raises(SkyPortalError) as err:
            sp_analysis.fetch_analysis_plot(analysis_id, plot_number=0)
        assert err.value.status_code == 404

        # try to get a non-existing results
        with pytest.raises(SkyPortalError, match="No data found") as err:
            sp_analysis.fetch_analysis_results(analysis_id)
        assert err.value.status_code == 404


def test_upload_analysis(
    analysis_service_token, analysis_token, public_group, public_source, view_only_token
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vesto Slipher",
            contact_email="vs@ls.st",
            url="http://example.com",
            authentication_type="none",
            analysis_type="meta_analysis",
            # the original payload omitted input_data_types; [] is the server default
            input_data_types=[],
            upload_only=True,
            group_ids=[public_group.id],
        )
    ).id

    # this should fail because the analysis service is an upload_only service
    # and the normal analysis endpoint (which kicks off a webhook) is
    # not allowed.
    with pytest.raises(SkyPortalError, match="analysis_upload endpoint") as err:
        sp_analysis.post_analysis(public_source.id, analysis_service_id)
    assert err.value.status_code == 403

    # this should succeed as the correct endpoint is being used for an
    # upload_only service
    sp_analysis.post_analysis_upload(
        public_source.id,
        analysis_service_id,
        AnalysisUploadPost(
            show_parameters=True,
            analysis={
                "results": {
                    "format": "json",
                    "data": {"external_provenance_id": str(uuid.uuid4())},
                }
            },
        ),
    )

    # this should succeed but we should be warned that we didn't
    # provide any analysis results
    upload = sp_analysis.post_analysis_upload(
        public_source.id,
        analysis_service_id,
        AnalysisUploadPost(show_parameters=True),
    )
    assert upload.message.find("empty analysis upload_only results") != -1

    # this should fail because the user's token does not have "Run Analyses"
    # persmissions
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_analysis_upload(
            public_source.id,
            analysis_service_id,
            AnalysisUploadPost(show_parameters=True),
        )
    assert err.value.status_code == 401


def test_run_analysis_with_file_input(
    analysis_service_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())

    optional_analysis_parameters = {
        "image_data": {"type": "file", "required": "True", "description": "Image data"},
        "fluxcal_data": {"type": "file", "description": "Fluxcal data"},
        "centroid_X": {"type": "number"},
        "centroid_Y": {"type": "number"},
        "spaxel_buffer": {"type": "number"},
    }

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="Spectral_Cube_Analysis",
            description="Spectral_Cube_Analysis description",
            version="1.0",
            contact_name="Michael Coughlin",
            # this is the URL/port of the Spectral_Cube_Analysis service that will be running during testing
            url="http://localhost:7003/analysis/spectral_cube_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="spectrum_fitting",
            input_data_types=[],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    datafile = f"{os.path.dirname(__file__)}/../../data/spectral_cube_analysis.fits"
    with open(datafile, "rb") as fid:
        payload = fid.read()

    payload = f"data:image/fits;name=spectral_cube_analysis.fits;base64,{base64.b64encode(payload).decode('utf-8')}"

    analysis_id = sp_analysis.post_analysis(
        public_source.id,
        analysis_service_id,
        AnalysisPost(
            show_parameters=True,
            show_plots=True,
            show_corner=True,
            analysis_parameters={"image_data": payload},
        ),
    ).id
    assert analysis_id is not None

    def analysis_started():
        analysis = sp_analysis.fetch_analysis(analysis_id, include_analysis_data=True)
        assert analysis.analysis_service_id == analysis_service_id
        assert analysis.status != "queued", (
            f"analysis was not started properly ({analysis.status_message})"
        )

    retry_until(analysis_started, timeout=100)


def test_default_analysis(
    analysis_service_token,
    analysis_token,
    public_group,
    public_source,
    taxonomy_token,
    classification_token,
):
    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name=taxonomy_name,
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    sp_classification = client(classification_token)

    name = str(uuid.uuid4())

    optional_analysis_parameters = {"test_parameters": ["test_value_1", "test_value_2"]}

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test default analysis service name",
            description="A test default analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            # this is the URL/port of the SN analysis service that will be running during testing
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            optional_analysis_parameters=json.dumps(optional_analysis_parameters),
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    default_analysis_id = sp_analysis.post_default_analysis(
        analysis_service_id,
        DefaultAnalysisPost(
            default_analysis_parameters={
                "test_parameters": "test_value_1",
            },
            group_ids=[public_group.id],
            source_filter={"classifications": [{"name": "Algol", "probability": 0.5}]},
            daily_limit=1,
        ),
    ).id

    # insert a classification which probability is too low to trigger the default analysis
    sp_classification.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=0.4,
            group_ids=[public_group.id],
        )
    )

    n_retries = 0
    while n_retries < 10:
        analyses = sp_analysis.fetch_analyses(
            obj_id=public_source.id, analysis_service_id=analysis_service_id
        )
        if len(analyses) == 1:
            assert False
        else:
            time.sleep(1)
            n_retries += 1

    # insert a classification which probability is high enough to trigger the default analysis
    sp_classification.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=0.9,
            group_ids=[public_group.id],
        )
    )

    n_retries = 0
    while n_retries < 20:
        analyses = sp_analysis.fetch_analyses(
            obj_id=public_source.id, analysis_service_id=analysis_service_id
        )
        if len(analyses) == 1:
            break
        else:
            time.sleep(1)
            n_retries += 1

    assert n_retries < 20

    # verify that the daily limit is respected, i.e. that the default analysis is not run again
    sp_classification.post_classification(
        ClassificationPost(
            obj_id=public_source.id,
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=0.9,
            group_ids=[public_group.id],
        )
    )

    n_retries = 0
    while n_retries < 10:
        analyses = sp_analysis.fetch_analyses(
            obj_id=public_source.id, analysis_service_id=analysis_service_id
        )
        if len(analyses) == 2:
            assert False
        else:
            time.sleep(1)
            n_retries += 1

    sp_analysis.delete_default_analysis(analysis_service_id, default_analysis_id)


def test_source_analysis(
    analysis_service_token, view_only_token, analysis_token, public_group, public_source
):
    sp_service = client(analysis_service_token)
    name = str(uuid.uuid4())

    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test analysis service name",
            description="A test analysis service description",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=["photometry", "redshift"],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    analysis_id = (
        client(analysis_token).post_analysis(public_source.id, analysis_service_id).id
    )
    assert analysis_id is not None

    source = client(view_only_token).fetch_source(
        public_source.id, include_analyses=True
    )
    assert any(analysis.id == analysis_id for analysis in source.analyses)


def test_default_analysis_on_save(
    analysis_service_token,
    analysis_token,
    upload_data_token,
    public_group,
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    # A (non-upload_only) analysis service backed by the demo analysis server.
    name = str(uuid.uuid4())
    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test default analysis on save",
            description="A test default analysis (save-to-group trigger)",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=[],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    # A default analysis that triggers when a source is saved to public_group
    # (source_filter pins a group_id rather than a classification).
    sp_analysis.post_default_analysis(
        analysis_service_id,
        DefaultAnalysisPost(
            default_analysis_parameters={},
            group_ids=[public_group.id],
            source_filter={"group_id": public_group.id},
            daily_limit=5,
        ),
    )

    # Saving a NEW source to that group should auto-trigger the default analysis.
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=24.6258,
            dec=-32.9024,
            redshift=0.1,
            group_ids=[public_group.id],
        )
    )

    n_retries = 0
    while n_retries < 20:
        analyses = sp_analysis.fetch_analyses(
            obj_id=obj_id, analysis_service_id=analysis_service_id
        )
        if len(analyses) == 1:
            break
        time.sleep(1)
        n_retries += 1

    assert n_retries < 20, (
        "default analysis was not triggered by saving the source to the group"
    )


def test_default_analysis_multiple_per_service(
    analysis_service_token,
    analysis_token,
    public_group,
):
    sp_service = client(analysis_service_token)
    sp_analysis = client(analysis_token)
    name = str(uuid.uuid4())
    analysis_service_id = sp_service.post_analysis_service(
        AnalysisServicePost(
            name=name,
            display_name="test multiple default analyses",
            description="A test service allowing multiple default analyses",
            version="1.0",
            contact_name="Vera Rubin",
            contact_email="vr@ls.st",
            url=f"http://localhost:{analysis_port}/analysis/demo_analysis",
            authentication_type="none",
            analysis_type="lightcurve_fitting",
            input_data_types=[],
            timeout=60,
            group_ids=[public_group.id],
        )
    ).id

    # Multiple default analyses on the SAME service are allowed (repeats):
    # different triggers, or the same trigger with different parameters.
    for source_filter in (
        {"classifications": [{"name": "Algol", "probability": 0.5}]},
        {"group_id": public_group.id},
    ):
        sp_analysis.post_default_analysis(
            analysis_service_id,
            DefaultAnalysisPost(
                default_analysis_parameters={},
                group_ids=[public_group.id],
                source_filter=source_filter,
                daily_limit=5,
            ),
        )

    assert len(sp_analysis.fetch_default_analyses(analysis_service_id)) == 2
