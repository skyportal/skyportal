import asyncio
import tempfile
import time
import uuid
from pathlib import Path

import conesearch_alchemy as ca
import sqlalchemy as sa
from astroquery.mast import MastMissions

from baselayer.app import models
from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db, session_context_id
from baselayer.log import make_log
from skyportal.handlers.api.spectrum import post_spectrum
from skyportal.models import Instrument, Obj, Source, Spectrum
from skyportal.utils.mast import (
    read_hst_x1d,
    read_jwst_x1d,
    recent_hst_datasets,
    recent_jwst_datasets,
    spectrum_products,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log("mast_retrieval")

init_db(**cfg["database"])

mast_cfg = cfg.get("mast", {})

enabled = mast_cfg.get("enabled", False)
interval = mast_cfg.get("interval_seconds", 3600)
look_back_days = mast_cfg.get("look_back_days", 7)
radius_arcsec = mast_cfg.get("radius_arcsec", 2.0)
exp_types = mast_cfg.get("exp_types") or [
    "NRS_FIXEDSLIT",
    "NRS_IFU",
    "MIR_MRS",
    "MIR_LRS-FIXEDSLIT",
]
hst_instruments = mast_cfg.get("hst_instruments") or ["STIS", "COS"]
instruments = mast_cfg.get("instruments") or {
    "NIRSPEC": "NIRSpec",
    "MIRI": "MIRI",
    "STIS": "STIS",
    "COS": "COS",
}
group_ids = mast_cfg.get("group_ids") or []
bot_user_id = mast_cfg.get("bot_user_id")


def is_configured():
    if not enabled:
        log("MAST retrieval disabled (set mast.enabled: true to enable)")
        return False
    missing = [
        name
        for name, value in {
            "mast.bot_user_id": bot_user_id,
            "mast.group_ids": group_ids,
        }.items()
        if not value
    ]
    if missing:
        log(f"Not retrieving MAST spectra, missing config: {', '.join(missing)}")
        return False
    return True


def matching_sources(session, ra, dec):
    return session.scalars(
        sa.select(Obj).where(
            Obj.within(ca.Point(ra=ra, dec=dec), radius_arcsec / 3600),
            sa.exists().where(Source.obj_id == Obj.id, Source.active.is_(True)),
        )
    ).all()


def already_ingested(session, obj_id, filename):
    return (
        session.scalar(
            sa.select(Spectrum.id).where(
                Spectrum.obj_id == obj_id,
                Spectrum.original_file_filename == filename,
            )
        )
        is not None
    )


async def _post_spectrum(data):
    async with models.async_plain_session_factory() as session:
        await post_spectrum(data, bot_user_id, session)


def ingest_dataset(missions, dataset, skipped):
    with DBSession() as session:
        objs = [
            (obj.id, obj.ra, obj.dec)
            for obj in matching_sources(session, dataset["ra"], dataset["dec"])
        ]
        if not objs:
            return 0
        instrument_name = instruments.get(dataset["instrument"])
        instrument_id = session.scalar(
            sa.select(Instrument.id).where(Instrument.name == instrument_name)
        )
    if instrument_id is None:
        log(
            f"No instrument named {instrument_name} for {dataset['instrument']}, "
            f"skipping {dataset['name']}"
        )
        return 0

    products = missions.get_product_list(dataset["name"])
    posted = 0
    for product in spectrum_products(products, dataset):
        filename = str(product["filename"])
        if filename in skipped:
            continue
        with DBSession() as session:
            pending = [
                obj for obj in objs if not already_ingested(session, obj[0], filename)
            ]
        if not pending:
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / filename
            status, msg, _ = missions.download_file(
                str(product["uri"]), local_path=path, cache=False, verbose=False
            )
            if status != "COMPLETE":
                log(f"Could not download {filename}: {msg}")
                continue

            found = False
            for obj_id, obj_ra, obj_dec in pending:
                spectra = (
                    read_hst_x1d(path, dataset["mjd"])
                    if dataset["mission"] == "hst"
                    else read_jwst_x1d(
                        path,
                        obj_ra,
                        obj_dec,
                        radius_arcsec,
                        default_mjd=dataset["mjd"],
                    )
                )
                for spectrum in spectra:
                    found = True
                    try:
                        asyncio.run(
                            _post_spectrum(
                                {
                                    **spectrum,
                                    "obj_id": obj_id,
                                    "instrument_id": instrument_id,
                                    "group_ids": group_ids,
                                    "origin": "MAST",
                                    "original_file_filename": filename,
                                    "altdata": {
                                        "dataset": dataset["name"],
                                        "program": dataset["program"],
                                    },
                                }
                            )
                        )
                        posted += 1
                    except Exception as e:
                        log(f"Could not add {filename} to {obj_id}: {e}")
            if not found:
                skipped.add(filename)
    return posted


def poll_once(clients, skipped):
    session_context_id.set(uuid.uuid4().hex)
    datasets = []
    for mission, recent_datasets, criteria in (
        ("jwst", recent_jwst_datasets, exp_types),
        ("hst", recent_hst_datasets, hst_instruments),
    ):
        try:
            datasets += recent_datasets(clients[mission], look_back_days, criteria)
        except Exception as e:
            log(f"Error querying {mission.upper()} datasets: {e}")
    posted = 0
    for dataset in datasets:
        if not dataset["public"]:
            continue
        try:
            posted += ingest_dataset(clients[dataset["mission"]], dataset, skipped)
        except Exception as e:
            log(f"Error retrieving {dataset['name']}: {e}")
    if posted:
        log(f"Added {posted} spectra from MAST")


@check_loaded(logger=log)
def service(*args, **kwargs):
    clients = {mission: MastMissions(mission=mission) for mission in ("jwst", "hst")}
    skipped = set()
    log(f"Retrieving JWST and HST spectra from MAST every {interval}s")
    while True:
        try:
            poll_once(clients, skipped)
        except Exception as e:
            log(f"Error retrieving spectra from MAST: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    try:
        if is_configured():
            service()
    except Exception as e:
        log(f"Error starting MAST retrieval service: {e}")

    while True:
        time.sleep(3600)
