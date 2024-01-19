from skyportal.utils.earthquake import get_country


def test_get_country():
    # minneapolis
    latitude = 44.9778
    longitude = -93.2650

    country = get_country(latitude, longitude)
    assert country == "United States of America"
