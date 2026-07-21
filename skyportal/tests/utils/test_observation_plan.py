from skyportal.utils.observation_plan import combine_healpix_tuples


def test_non_overlapping_tiles_unchanged():
    assert set(combine_healpix_tuples([(0, 10), (20, 30)])) == {(0, 10), (20, 30)}


def test_overlapping_tiles_merge_to_union():
    assert set(combine_healpix_tuples([(0, 10), (5, 15)])) == {(0, 15)}


def test_chained_overlaps_merge_into_one():
    assert set(combine_healpix_tuples([(0, 10), (5, 15), (14, 20)])) == {(0, 20)}


def test_touching_boundaries_are_not_merged():
    # (0, 10) and (10, 20) only touch at 10; 10 < 10 is False -> not overlapping
    assert set(combine_healpix_tuples([(0, 10), (10, 20)])) == {(0, 10), (10, 20)}


def test_duplicates_removed():
    assert set(combine_healpix_tuples([(0, 10), (0, 10)])) == {(0, 10)}


def test_single_and_empty_inputs():
    assert set(combine_healpix_tuples([(0, 10)])) == {(0, 10)}
    assert combine_healpix_tuples([]) == []
