from skyportal.utils.gcn_crossmatch import (
    NDETHIST_FIELD,
    POSITION_FIELD,
    with_fields_projected,
)


def test_an_inclusion_without_position_gains_it():
    assert with_fields_projected(
        [{"$project": {"objectId": 1, "candidate": 1}}],
        (POSITION_FIELD, NDETHIST_FIELD),
    ) == [
        {
            "$project": {
                "objectId": 1,
                "candidate": 1,
                "coordinates.radec_geojson": 1,
            }
        }
    ]


def test_an_inclusion_of_galactic_coordinates_still_gains_position():
    assert with_fields_projected(
        [{"$project": {"objectId": 1, "coordinates.b": 1}}], (POSITION_FIELD,)
    ) == [
        {
            "$project": {
                "objectId": 1,
                "coordinates.b": 1,
                "coordinates.radec_geojson": 1,
            }
        }
    ]


def test_an_exclusion_stops_excluding_position():
    assert with_fields_projected(
        [{"$project": {"coordinates.radec_geojson": 0, "coordinates.b": 0}}],
        (POSITION_FIELD,),
    ) == [{"$project": {"coordinates.b": 0}}]
