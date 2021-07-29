import os
import pandas as pd

from skyportal.utils.instrument import get_ztf_quadrants, get_mocs


def test_get_ztf_quadrants():
    quad = get_ztf_quadrants()
    assert quad.shape == (2, 64, 4)


def test_get_mocs():

    datafile = f'{os.path.dirname(__file__)}/../../../data/input/ZTF_Fields.csv'
    field_data = pd.read_csv(datafile).iloc[:10].to_dict(orient='list')
    field_of_view_shape = "square"
    field_of_view_size = 6.83

    mocs = get_mocs(
        field_data, field_of_view_shape, field_of_view_size=field_of_view_size
    )
    assert len(mocs) == 10

    field_of_view_shape = "circle"
    mocs = get_mocs(
        field_data, field_of_view_shape, field_of_view_size=field_of_view_size
    )
    assert len(mocs) == 10

    field_of_view_shape = "ZTF"
    mocs = get_mocs(field_data, field_of_view_shape)
    assert len(mocs) == 10
