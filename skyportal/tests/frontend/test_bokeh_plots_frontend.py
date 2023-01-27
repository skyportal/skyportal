import time
import pytest
from selenium.webdriver.common.by import By

from baselayer.app.config import load_config

cfg = load_config()


def expand_shadow_element(driver, element):
    shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
    return shadow_root


@pytest.mark.flaky(reruns=3)
def test_export_bold_light_curve_as_csv_button(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath('//div[@class=" bk-root"]', timeout=20)

    num_panels = 0
    nretries = 0
    while num_panels < 2 and nretries < 30:
        panels = driver.find_elements(By.XPATH, "//*[contains(@id,'bokeh')]")
        num_panels = len(panels)
        if num_panels == 2:
            break
        nretries = nretries + 1
        time.sleep(5)

    button_present = False
    for panel in panels:
        if "Export Bold Light Curve to CSV" in panel.text:
            button_present = True

    assert button_present

    # btn = driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    # driver.scroll_to_element_and_click(btn)
    # assert f"{public_source.id}.csv" in os.listdir(
    #    os.path.abspath(cfg["paths.downloads_folder"])
    # )
