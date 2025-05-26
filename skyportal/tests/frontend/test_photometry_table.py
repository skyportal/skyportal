import csv
import os
import time
from datetime import datetime, timezone
from os.path import join

import pytest
from astropy.time import Time
from selenium.webdriver.common.by import By

from baselayer.app.config import load_config

cfg = load_config()

DEFAULT_PHOTOMETRY_COLUMNS = [
    "id",
    "mjd",
    "mag",
    "magerr",
    "limiting_mag",
    "filter",
    "instrument_name",
]
ALL_PHOTOMETRY_COLUMNS = DEFAULT_PHOTOMETRY_COLUMNS + [
    "altdata",
    "created_at",
    "dec",
    "dec_unc",
    "flux",
    "fluxerr",
    "instrument_id",
    "magsys",
    "origin",
    "owner",
    "ra",
    "ra_unc",
    "snr",
    "streams",
    "utc",
]


def test_download_photometry_table_default(driver, super_admin_user, public_source):
    """Test opening the download options dialog."""

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    phot_table_button = driver.wait_for_xpath_to_be_clickable(
        '*//button[@data-testid="show-photometry-table-button"]',
        timeout=10,
    )
    phot_table_button.click()

    driver.wait_for_xpath('//div[contains(@class, "MuiDialog-root")]')
    driver.wait_for_xpath('//div[contains(@class, "MUIDataTableToolbar")]')

    download_button = driver.wait_for_xpath_to_be_clickable(
        '//div[contains(@class, "MuiDialog-root")]//button[@aria-label="Download CSV"]',
        timeout=10,
    )
    download_button.click()

    driver.wait_for_xpath('//h6[contains(text(), "Download Options")]')
    default_columns_button = driver.wait_for_xpath_to_be_clickable(
        '//button[contains(text(), "Default")]'
    )
    default_columns_button.click()
    driver.wait_for_xpath('//button[contains(text(), "All")]')
    driver.wait_for_xpath('//button[@data-testid="download-photometry-table-button"]')

    execute_download_button = driver.wait_for_xpath_to_be_clickable(
        '//button[@data-testid="download-photometry-table-button"]',
        timeout=10,
    )
    execute_download_button.click()

    file_path = str(
        os.path.abspath(
            join(cfg["paths.downloads_folder"], f"{public_source.id}_photometry.csv")
        )
    )

    try_count = 1
    while not os.path.exists(file_path) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(file_path)

    try:
        with open(file_path) as f:
            reader = csv.reader(f)
            columns = next(reader)
        assert len(columns) == len(DEFAULT_PHOTOMETRY_COLUMNS)
        for col in DEFAULT_PHOTOMETRY_COLUMNS:
            assert col in columns

    finally:
        os.remove(file_path)


def test_download_photometry_table_all(driver, super_admin_user, public_source):
    """Test opening the download options dialog."""

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    phot_table_button = driver.wait_for_xpath_to_be_clickable(
        '*//button[@data-testid="show-photometry-table-button"]',
        timeout=10,
    )
    phot_table_button.click()

    driver.wait_for_xpath('//div[contains(@class, "MuiDialog-root")]')
    driver.wait_for_xpath('//div[contains(@class, "MUIDataTableToolbar")]')

    download_button = driver.wait_for_xpath_to_be_clickable(
        '//div[contains(@class, "MuiDialog-root")]//button[@aria-label="Download CSV"]',
        timeout=10,
    )
    download_button.click()

    driver.wait_for_xpath('//h6[contains(text(), "Download Options")]')
    driver.wait_for_xpath('//button[contains(text(), "Default")]')
    all_columns_button = driver.wait_for_xpath_to_be_clickable(
        '//button[contains(text(), "All")]'
    )
    all_columns_button.click()
    driver.wait_for_xpath('//button[@data-testid="download-photometry-table-button"]')

    execute_download_button = driver.wait_for_xpath_to_be_clickable(
        '//button[@data-testid="download-photometry-table-button"]',
        timeout=10,
    )
    execute_download_button.click()

    file_path = str(
        os.path.abspath(
            join(cfg["paths.downloads_folder"], f"{public_source.id}_photometry.csv")
        )
    )

    try_count = 1
    while not os.path.exists(file_path) and try_count <= 5:
        try_count += 1
        time.sleep(1)
    assert os.path.exists(file_path)

    try:
        with open(file_path) as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)
            columns = list(csv_data[0].keys())
        assert len(columns) == len(ALL_PHOTOMETRY_COLUMNS)
        for col in ALL_PHOTOMETRY_COLUMNS:
            assert col in columns

        phot = public_source.photometry[0].to_dict()
        assert csv_data[0]["filter"] == phot["filter"]
        assert int(csv_data[0]["id"]) == phot["id"]
        assert int(csv_data[0]["flux"]) == int(phot["flux"])
        phot_utc = Time(phot["mjd"], format="mjd")
        assert datetime.fromisoformat(
            csv_data[0]["utc"][:-1] + "+00:00"
        ) == phot_utc.datetime.replace(microsecond=0, tzinfo=timezone.utc)

    finally:
        os.remove(file_path)
