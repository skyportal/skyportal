import types

from skyportal.utils.trove_submission import create_payload

OBJ = types.SimpleNamespace(id="ZTF26abc", ra=10.0, dec=-20.0)


def _phot(mag=None, magerr=None, limiting_mag=None):
    return types.SimpleNamespace(
        jd=2460000.5,
        instrument=types.SimpleNamespace(
            name="ZTF", telescope=types.SimpleNamespace(nickname="P48")
        ),
        to_dict_public=lambda: {
            "mag": mag,
            "magerr": magerr,
            "limiting_mag": limiting_mag,
            "filter": "ztfr",
        },
    )


def test_detection():
    (point,) = create_payload(OBJ, [_phot(19.7, 0.08, 20.5)])["photometry"]
    assert point == {
        "jd": 2460000.5,
        "telescope": "P48-ZTF",
        "filter": "ztfr",
        "magnitude": 19.7,
        "error": 0.08,
    }


def test_non_detection_sends_only_the_limit():
    (point,) = create_payload(OBJ, [_phot(limiting_mag=20.3)])["photometry"]
    assert point["limit"] == 20.3
    assert "magnitude" not in point
    assert "error" not in point


def test_point_without_mag_or_limit_is_skipped():
    payload = create_payload(OBJ, [_phot()])
    assert "photometry" not in payload


def test_target_fields():
    payload = create_payload(OBJ, [])
    assert payload == {
        "name": "ZTF26abc",
        "ra": 10.0,
        "dec": -20.0,
        "permissions": "PUBLIC",
        "type": "SIDEREAL",
        "epoch": 2000,
    }
