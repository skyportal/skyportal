import os
from baselayer.app.config import load_config

cfg = load_config()


def test_export_bold_light_curve_as_csv_button(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    btn = driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    driver.scroll_to_element_and_click(btn)
    assert f"{public_source.id}.csv" in os.listdir(
        os.path.abspath(cfg["paths.downloads_folder"])
    )
