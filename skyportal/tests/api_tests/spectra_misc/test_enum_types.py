from skyportal.tests import client


def test_enum_types_api(upload_data_token, super_admin_token):
    # get the enum types
    enum_types = client(upload_data_token).fetch_enum_types()

    enum_types_list = [
        "ALLOWED_SPECTRUM_TYPES",
        "ALLOWED_MAGSYSTEMS",
        "ALLOWED_BANDPASSES",
        "THUMBNAIL_TYPES",
        "FOLLOWUP_PRIORITIES",
        "ALLOWED_API_CLASSNAMES",
    ]

    assert all(enum_type in enum_types for enum_type in enum_types_list)
