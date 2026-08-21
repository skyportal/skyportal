from skyportal.tests import client


def test_post_retrieve_color_mag_data(annotation_token, user, public_source):
    sp = client(annotation_token)
    annotation_id = sp.post_annotation(
        public_source.id,
        "gaiadr3.gaia_source",
        {
            "Mag_G": 15.1,
            "Mag_Bp": 16.1,
            "Mag_Rp": 14.0,
            "Plx": 20,
        },
    ).annotation_id

    color_mag = sp.fetch_source_color_mag(public_source.id)

    assert color_mag[0].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # add absorption by an edit to the annotation
    sp.update_annotation(
        public_source.id,
        annotation_id,
        {
            "Mag_G": 15.1,
            "Mag_Bp": 16.1,
            "Mag_Rp": 14.0,
            "Plx": 20,
            "A_G": 0.3,
        },
    )

    color_mag = sp.fetch_source_color_mag(public_source.id)

    assert color_mag[0].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.9) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # replace the magnitude in apparent bands with the absolute mag and color
    sp.update_annotation(
        public_source.id,
        annotation_id,
        {
            "Mag_G": 15.1,
            "Mag_Bp": 16.1,
            "Mag_Rp": 14.0,
            "Plx": 20,
            "Abs_mag_G": 12.5,
            "color": 1.8,
        },
        # note the additional keys should override the existing data only when asking for them in the query
    )

    # here we are not requesting the abs-mag and color, so the response should be the same as before
    color_mag = sp.fetch_source_color_mag(public_source.id)

    assert color_mag[0].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # here the request asks for the specific keys for abs-mag and color
    color_mag = sp.fetch_source_color_mag(
        public_source.id, absolute_mag_key="abs_mag_g", color_key="color"
    )

    assert color_mag[0].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[0].abs_mag - 12.5) < 0.1
    assert abs(color_mag[0].color - 1.8) < 0.1

    # check that the source also provides the same info (with default keys!)
    source = client(annotation_token).fetch_source(
        public_source.id, include_color_magnitude=True
    )
    assert source.color_magnitude[0].origin == "gaiadr3.gaia_source"
    assert abs(source.color_magnitude[0].abs_mag - 11.6) < 0.1
    assert abs(source.color_magnitude[0].color - 2.1) < 0.1


def test_change_color_mag_keys(annotation_token, user, public_source):
    sp = client(annotation_token)
    annotation_id = sp.post_annotation(
        public_source.id,
        "gaiadr3.gaia_source",
        {"MagG": 15.1, "MagBp": 16.1, "MagRp": 14.0, "Plx": 20},
    ).annotation_id

    color_mag = sp.fetch_source_color_mag(public_source.id)

    assert color_mag[0].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # change the keys, replace capital letters with underscores
    sp.update_annotation(
        public_source.id,
        annotation_id,
        {"mag_g": 15.1, "mag_bp": 16.1, "mag_rp": 14.0, "plx": 20},
    )

    color_mag = sp.fetch_source_color_mag(public_source.id)

    assert color_mag[0].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # change the keys to completely new names, rename the catalog as well
    sp.update_annotation(
        public_source.id,
        annotation_id,
        {"mag4.6": 15.1, "Mag_3.3": 16.1, "Mag_12": 14.0, "plx": 20},
        origin="wise_colors",
    )

    color_mag = sp.fetch_source_color_mag(
        public_source.id,
        catalog="wise",
        apparent_mag_key="Mag_4.6",
        blue_mag_key="Mag_3.3",
        red_mag_key="Mag_12",
    )

    assert color_mag[0].origin == "wise_colors"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1


def test_add_multiple_color_mag_annotations(annotation_token, user, public_source):
    sp = client(annotation_token)
    sp.post_annotation(
        public_source.id,
        "gaiadr1.gaia_source",
        {"MagG": 15.1, "MagBp": 16.1, "MagRp": 14.0, "Plx": 20},
    )

    color_mag = sp.fetch_source_color_mag(public_source.id)

    assert color_mag[0].origin == "gaiadr1.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # post from a second origin
    sp.post_annotation(
        public_source.id,
        "gaiadr2.gaia_source",
        {"MagG": 15.2, "MagBp": 16.2, "MagRp": 14.0, "Plx": 20},
    )

    # post from a third origin
    sp.post_annotation(
        public_source.id,
        "gaiadr3.gaia_source",
        {"MagG": 15.3, "MagBp": 16.3, "MagRp": 14.0, "Plx": 5},
    )

    color_mag = sp.fetch_source_color_mag(public_source.id)

    # make sure the dictionaries are sorted
    color_mag = sorted(color_mag, key=lambda x: x.origin)
    assert len(color_mag) == 3

    # make sure the first one still exists
    assert color_mag[0].origin == "gaiadr1.gaia_source"
    assert abs(color_mag[0].abs_mag - 11.6) < 0.1
    assert abs(color_mag[0].color - 2.1) < 0.1

    # make sure the second one still exists
    assert color_mag[1].origin == "gaiadr2.gaia_source"
    assert abs(color_mag[1].abs_mag - 11.7) < 0.1
    assert abs(color_mag[1].color - 2.2) < 0.1

    # make sure the last was added
    assert color_mag[2].origin == "gaiadr3.gaia_source"
    assert abs(color_mag[2].abs_mag - 8.8) < 0.1
    assert abs(color_mag[2].color - 2.3) < 0.1
