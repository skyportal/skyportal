import datetime


def test_problematic_timezone(wise_18inch, xinglong_216cm):
    assert (
        wise_18inch.observer_timezone.timezone.utcoffset(
            datetime.datetime.fromisoformat("2020-11-17T00:00:00")
        ).seconds
        / 3600
        == 2
    )

    assert (
        xinglong_216cm.observer_timezone.timezone.utcoffset(
            datetime.datetime.fromisoformat("2020-11-17T00:00:00")
        ).seconds
        / 3600
        == 8
    )
