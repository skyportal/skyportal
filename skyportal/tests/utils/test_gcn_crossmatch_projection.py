"""Keeping the alert position through a filter's own projection.

The filter builder projects only the fields a filter names, so a filter with
no positional criterion returned alerts carrying no position, and the
crossmatch dropped every one of them before it could create a candidate.
"""

from skyportal.utils.gcn_crossmatch import alert_position, with_position_projected


def test_a_projection_without_position_gains_one():
    # What the builder emits for a filter that never cuts on position.
    pipeline = [{"$project": {"objectId": 1, "candidate.jd": 1}}]
    assert with_position_projected(pipeline) == [
        {"$project": {"objectId": 1, "candidate.jd": 1, "coordinates": 1}}
    ]


def test_every_project_stage_is_patched_not_only_the_last():
    # The builder emits an initial $project as well as the terminal one, and a
    # field dropped by the first cannot be recovered by the last.
    patched = with_position_projected(
        [
            {"$project": {"objectId": 1, "candidate.jd": 1}},
            {"$match": {"candidate.drb": {"$gt": 0.5}}},
            {"$project": {"objectId": 1}},
        ]
    )
    assert [
        stage["$project"]["coordinates"] for stage in patched if "$project" in stage
    ] == [1, 1]
    assert patched[1] == {"$match": {"candidate.drb": {"$gt": 0.5}}}


def test_a_projection_that_already_keeps_position_is_untouched():
    for spec in ({"objectId": 1, "coordinates": 1}, {"coordinates.radec_geojson": 1}):
        pipeline = [{"$project": spec}]
        assert with_position_projected(pipeline) == pipeline


def test_suppressing_id_alongside_inclusions_still_gains_position():
    # {"_id": 0} beside an inclusion is an inclusion projection, not an
    # exclusion one.
    assert with_position_projected([{"$project": {"_id": 0, "objectId": 1}}]) == [
        {"$project": {"_id": 0, "objectId": 1, "coordinates": 1}}
    ]


def test_an_exclusion_projection_keeps_position_instead_of_gaining_it():
    # An exclusion keeps everything it does not name, so position only has to
    # be rescued from the exclusion list.
    assert with_position_projected(
        [{"$project": {"coordinates": 0, "cutoutScience": 0}}]
    ) == [{"$project": {"cutoutScience": 0}}]


def test_a_projection_that_only_dropped_position_is_removed():
    # Mongo rejects an empty $project, and the stage had no other purpose.
    assert with_position_projected([{"$project": {"coordinates": 0}}]) == []


def test_stages_without_a_projection_pass_through():
    pipeline = [{"$match": {"candidate.rb": {"$gt": 0.3}}}, {"$limit": 10}]
    assert with_position_projected(pipeline) == pipeline
    assert with_position_projected([]) == []
    assert with_position_projected(None) == []


def test_the_patched_projection_is_what_alert_position_reads():
    # The repair is only worth anything if the field it adds is the one the
    # position is actually recovered from.
    (stage,) = with_position_projected([{"$project": {"objectId": 1}}])
    field = next(key for key in stage["$project"] if key != "objectId")
    alert = {field: {"radec_geojson": {"coordinates": [-66.07, 41.2]}}}
    ra, dec = alert_position(alert)
    assert (round(ra, 2), round(dec, 2)) == (113.93, 41.2)
