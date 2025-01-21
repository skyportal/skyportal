from skyportal.tests import api


def test_post_retrieve_color_mag_data(annotation_token, user, public_source):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {
                "Mag_G": 15.1,
                "Mag_Bp": 16.1,
                "Mag_Rp": 14.0,
                "Plx": 20,
            },
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET",
        f"sources/{public_source.id}/color_mag",
        token=annotation_token,
        params={"includeColorMagnitude": True},
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # add absorption by an edit to the annotation
    status, data = api(
        "PUT",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {
                "Mag_G": 15.1,
                "Mag_Bp": 16.1,
                "Mag_Rp": 14.0,
                "Plx": 20,
                "A_G": 0.3,
            },
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/color_mag", token=annotation_token
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.9) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # replace the magnitude in apparent bands with the absolute mag and color
    status, data = api(
        "PUT",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {
                "Mag_G": 15.1,
                "Mag_Bp": 16.1,
                "Mag_Rp": 14.0,
                "Plx": 20,
                "Abs_mag_G": 12.5,
                "color": 1.8,
            },
            # note the additional keys should override the existing data only when asking for them in the query
        },
        token=annotation_token,
    )
    assert status == 200

    # here we are not requesting the abs-mag and color, so the response should be the same as before
    status, data = api(
        "GET", f"sources/{public_source.id}/color_mag", token=annotation_token
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # here the request asks for the specific keys for abs-mag and color
    status, data = api(
        "GET",
        f"sources/{public_source.id}/color_mag",
        params={"absoluteMagKey": "abs_mag_g", "colorKey": "color"},
        token=annotation_token,
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 12.5) < 0.1
    assert abs(data["data"][0]["color"] - 1.8) < 0.1

    # check that the source also provides the same info (with default keys!)
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        token=annotation_token,
        params={"includeColorMagnitude": True},
    )

    assert status == 200
    assert data["data"]["color_magnitude"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"]["color_magnitude"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"]["color_magnitude"][0]["color"] - 2.1) < 0.1


def test_change_color_mag_keys(annotation_token, user, public_source):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {"MagG": 15.1, "MagBp": 16.1, "MagRp": 14.0, "Plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data["data"]["annotation_id"]

    status, data = api(
        "GET", f"sources/{public_source.id}/color_mag", token=annotation_token
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # change the keys, replace capital letters with underscores
    status, data = api(
        "PUT",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {"mag_g": 15.1, "mag_bp": 16.1, "mag_rp": 14.0, "plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/color_mag", token=annotation_token
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # change the keys to completely new names, rename the catalog as well
    status, data = api(
        "PUT",
        f"sources/{public_source.id}/annotations/{annotation_id}",
        data={
            "obj_id": public_source.id,
            "origin": "wise_colors",
            "data": {"mag4.6": 15.1, "Mag_3.3": 16.1, "Mag_12": 14.0, "plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source.id}/color_mag",
        params={
            "catalog": "wise",
            "apparentMagKey": "Mag_4.6",
            "blueMagKey": "Mag_3.3",
            "redMagKey": "Mag_12",
        },
        token=annotation_token,
    )

    assert status == 200
    assert data["data"][0]["origin"] == "wise_colors"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1


def test_add_multiple_color_mag_annotations(annotation_token, user, public_source):
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr1.gaia_source",
            "data": {"MagG": 15.1, "MagBp": 16.1, "MagRp": 14.0, "Plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/color_mag", token=annotation_token
    )

    assert status == 200
    assert data["data"][0]["origin"] == "gaiadr1.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # post from a second origin
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr2.gaia_source",
            "data": {"MagG": 15.2, "MagBp": 16.2, "MagRp": 14.0, "Plx": 20},
        },
        token=annotation_token,
    )
    assert status == 200

    # post from a third origin
    status, data = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "gaiadr3.gaia_source",
            "data": {"MagG": 15.3, "MagBp": 16.3, "MagRp": 14.0, "Plx": 5},
        },
        token=annotation_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{public_source.id}/color_mag", token=annotation_token
    )

    assert status == 200

    # make sure the dictionaries are sorted
    data["data"] = sorted(data["data"], key=lambda x: x["origin"])
    assert len(data["data"]) == 3

    # make sure the first one still exists
    assert data["data"][0]["origin"] == "gaiadr1.gaia_source"
    assert abs(data["data"][0]["abs_mag"] - 11.6) < 0.1
    assert abs(data["data"][0]["color"] - 2.1) < 0.1

    # make sure the second one still exists
    assert data["data"][1]["origin"] == "gaiadr2.gaia_source"
    assert abs(data["data"][1]["abs_mag"] - 11.7) < 0.1
    assert abs(data["data"][1]["color"] - 2.2) < 0.1

    # make sure the last was added
    assert data["data"][2]["origin"] == "gaiadr3.gaia_source"
    assert abs(data["data"][2]["abs_mag"] - 8.8) < 0.1
    assert abs(data["data"][2]["color"] - 2.3) < 0.1
