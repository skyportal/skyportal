import uuid

from skyportal_py.sources import SourcePost

from skyportal.handlers.api.internal.altdata_info import cache as altdata_info_cache
from skyportal.handlers.api.internal.annotations_info import (
    cache as annotations_info_cache,
)
from skyportal.tests import client


def test_altdata_info(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    key = f"key_{uuid.uuid4().hex}"

    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=210.0,
            dec=-22.33,
            group_ids=[public_group.id],
            altdata={key: 1.5},
        )
    )

    # Clear the (global) cache so the freshly-posted key is reflected.
    del altdata_info_cache["altdata_info"]

    info = client(view_only_token).fetch_altdata_info()
    keys = info["keys"]
    entry = next((e for e in keys if key in e), None)
    assert entry is not None
    assert entry[key] == "number"


def test_annotations_info(upload_data_token, annotation_token, public_group):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=211.0,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )

    origin = f"origin_{uuid.uuid4().hex}"
    key = f"key_{uuid.uuid4().hex}"
    client(annotation_token).post_annotation(obj_id, origin, {key: 2.0})

    # Clear this user's cache so the new annotation is reflected.
    profile = client(annotation_token).fetch_profile()
    del annotations_info_cache[f"annotations_info_{profile.id}"]

    info = client(annotation_token).fetch_annotations_info()
    assert origin in info
    assert any(key in entry for entry in info[origin])
