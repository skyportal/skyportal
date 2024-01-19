import time
import pytest
from selenium.webdriver.common.by import By

from baselayer.app.config import load_config

cfg = load_config()


@pytest.mark.flaky(reruns=3)
def test_export_bold_light_curve_as_csv_button(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")

    button_present = False
    nretries = 0
    while button_present is False and nretries < 20:
        try:
            download_button = driver.find_elements(
                By.XPATH, "//*[contains(@id,'download-lightcurve-button')]"
            )
            if len(download_button) > 0:
                button_present = True
                break
            else:
                nretries += 1
                time.sleep(3)
        except Exception:
            nretries += 1
            time.sleep(3)

    assert button_present
