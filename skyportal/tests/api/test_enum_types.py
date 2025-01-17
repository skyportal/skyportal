from skyportal.tests import api


def test_enum_types_api(upload_data_token, super_admin_token):
    # get the enum types
    status, data = api("GET", "enum_types", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    enum_types_list = [
        "ALLOWED_SPECTRUM_TYPES",
        "ALLOWED_MAGSYSTEMS",
        "ALLOWED_BANDPASSES",
        "THUMBNAIL_TYPES",
        "FOLLOWUP_PRIORITIES",
        "ALLOWED_API_CLASSNAMES",
    ]

    assert all(enum_type in data["data"] for enum_type in enum_types_list)
