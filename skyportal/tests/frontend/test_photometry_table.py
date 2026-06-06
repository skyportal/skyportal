import csv
import os
from datetime import UTC, datetime
from os.path import join

from astropy.time import Time
from playwright.sync_api import expect

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
    "flux",
    "fluxerr",
]
ALL_PHOTOMETRY_COLUMNS = DEFAULT_PHOTOMETRY_COLUMNS + [
    "altdata",
    "created_at",
    "dec",
    "dec_unc",
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


def _open_download_options(page, super_admin_user, public_source):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")

    page.locator('//button[@data-testid="show-photometry-table-button"]').first.click()
    expect(
        page.locator('//div[contains(@class, "MuiDialog-root")]').first
    ).to_be_visible()
    expect(
        page.locator('//div[contains(@class, "MuiDataGrid-root")]').first
    ).to_be_visible()

    page.locator(
        '//div[contains(@class, "MuiDialog-root")]'
        '//button[@data-testid="open-photometry-download-button"]'
    ).first.click()
    expect(
        page.locator('//h6[contains(text(), "Download Options")]').first
    ).to_be_visible()


def _download_to(page, file_path):
    with page.expect_download() as download_info:
        page.locator(
            '//button[@data-testid="download-photometry-table-button"]'
        ).first.click()
    download_info.value.save_as(file_path)
    assert os.path.exists(file_path)


def test_download_photometry_table_default(page, super_admin_user, public_source):
    """Test downloading the photometry table with the default columns."""
    _open_download_options(page, super_admin_user, public_source)

    page.locator('//button[contains(text(), "Default")]').first.click()
    expect(page.locator('//button[contains(text(), "All")]').first).to_be_visible()
    expect(
        page.locator('//button[@data-testid="download-photometry-table-button"]').first
    ).to_be_visible()

    page.locator('//label[.//span[text()="Not vetted"]]').first.click()

    file_path = str(
        os.path.abspath(
            join(cfg["paths.downloads_folder"], f"{public_source.id}_photometry.csv")
        )
    )
    _download_to(page, file_path)

    try:
        with open(file_path) as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)
            columns = list(csv_data[0].keys())
        assert len(columns) == len(DEFAULT_PHOTOMETRY_COLUMNS)
        for col in DEFAULT_PHOTOMETRY_COLUMNS:
            assert col in columns

        phot = public_source.photometry[0].to_dict()
        assert csv_data[0]["filter"] == phot["filter"]
        assert int(csv_data[0]["id"]) == phot["id"]
        assert float(csv_data[0]["flux"]) - phot["flux"] < 0.001
    finally:
        os.remove(file_path)


def test_download_photometry_table_all(page, super_admin_user, public_source):
    """Test downloading the photometry table with all columns."""
    _open_download_options(page, super_admin_user, public_source)

    expect(page.locator('//button[contains(text(), "Default")]').first).to_be_visible()
    page.locator('//button[contains(text(), "All")]').first.click()
    expect(
        page.locator('//button[@data-testid="download-photometry-table-button"]').first
    ).to_be_visible()

    file_path = str(
        os.path.abspath(
            join(cfg["paths.downloads_folder"], f"{public_source.id}_photometry.csv")
        )
    )
    _download_to(page, file_path)

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
        assert float(csv_data[0]["flux"]) - phot["flux"] < 0.001
        phot_utc = Time(phot["mjd"], format="mjd")
        assert datetime.fromisoformat(
            csv_data[0]["utc"][:-1] + "+00:00"
        ) == phot_utc.datetime.replace(microsecond=0, tzinfo=UTC)
    finally:
        os.remove(file_path)
