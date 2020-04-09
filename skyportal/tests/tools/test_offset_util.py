import pytest
import uuid

from skyportal.utils import (
    get_nearby_offset_stars,
    source_image_parameters, get_finding_chart, get_ztfref_url
)


def test_get_ztfref_url():
    url = get_ztfref_url(123.0, 33.3, 2)

    assert isinstance(url, str)
    assert url.find("irsa") != -1


def test_get_nearby_offset_stars():
    how_many = 3
    rez = get_nearby_offset_stars(
        123.0, 33.3, "testSource",
        how_many=how_many,
        radius_degrees = 3/60.0
    )

    assert len(rez) == 4
    assert isinstance(rez[0], list)
    assert len(rez[0]) == how_many + 1


    with pytest.raises(Exception):
        rez = get_nearby_offset_stars(
            123.0, 33.3, "testSource",
            how_many=how_many,
            radius_degrees = 3/60.0,
            allowed_queries=1,
            queries_issued=2
        )

def test_get_finding_chart():

    rez = get_finding_chart(
        123.0, 33.3, "testSource",
        image_source='desi',
        output_format='pdf'
    )

    assert isinstance(rez, dict)
    assert rez["success"]
    assert rez["name"].find("testSource") != -1
    assert rez["data"].find(bytes("PDF", encoding='utf8')) != -1


    with pytest.raises(ValueError):
        rez = get_finding_chart(
            123.0, 33.3, "testSource",
            imsize=1.0
        )


    rez = get_finding_chart(
            123.0, 33.3, "testSource",
            image_source='zomg_telescope'
    )
    assert isinstance(rez, dict)
    assert not rez["success"]

