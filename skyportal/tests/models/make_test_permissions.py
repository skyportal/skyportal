import os

access_types = ["create", "read", "update", "delete"]
users = ["user", "user_group2", "super_admin_user", "group_admin_user"]
targets = [
    "public_group",
    "public_groupuser",
    "public_stream",
    "public_groupstream",
    "public_streamuser",
    "public_filter",
    "public_candidate_object",
    "public_source_object",
    "keck1_telescope",
    "sedm",
    "public_group_sedm_allocation",
    "public_group_taxonomy",
    "public_taxonomy",
    "public_comment",
    "public_groupcomment",
    "public_annotation",
    "public_groupannotation",
    "public_classification",
    "public_groupclassification",
    "public_source_photometry_point",
    "public_source_spectrum",
    "public_source_groupphotometry",
    "public_source_groupspectrum",
    "public_source_followuprequest",
    "public_source_followup_request_target_group",
    "public_thumbnail",
    "red_transients_run",
    "problematic_assignment",
    "invitation",
    "user_notification",
]


directory = os.path.dirname(__file__)
fname = os.path.join(directory, "test_permissions.py")

with open(fname, "w") as f:
    for user in users:
        for access_type in access_types:
            for target in targets:
                test = f"""
def test_{user}_{access_type}_{target}({user}, {target}):
    accessible = {target}.is_accessible_by({user}, mode="{access_type}")
    assert accessible == accessible

"""
                f.write(test)
