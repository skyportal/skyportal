import datetime


def test_problematic_timezone(wise_18inch):
    assert (
        wise_18inch.observer.timezone.utcoffset(
            datetime.datetime.fromisoformat('2020-11-17T00:00:00')
        ).seconds
        / 3600
        == 2
    )
