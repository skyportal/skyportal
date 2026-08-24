"""Containment tests for the GCN crossmatch geometry helpers.

The crossmatch queries a broker with a bounding cone and then decides membership
with an exact containment check. The cone path is analytic; the skymap path runs
a HEALPix containment query against the stored localization tiles, and that query
is the part most likely to be quietly wrong -- so it is exercised here against a
real localization built by the app, not a hand-made fixture.
"""

import asyncio
import time
import uuid
from datetime import timedelta

import numpy as np
import pytest
import sqlalchemy as sa

from baselayer.app import models
from skyportal.models import Localization
from skyportal.tests import api
from skyportal.utils.calculations import gaussian_sigmas_for
from skyportal.utils.crossmatch import (
    contained_in_localization,
    credible_levels_in_localization,
    search_cone,
)
from skyportal.utils.naive_datetime import utcnow_naive


def _unique_dateobs():
    return (
        utcnow_naive() - timedelta(seconds=int(np.random.randint(10**5, 10**7)))
    ).replace(microsecond=0)


def _wait_for_tiles(localization_id, timeout=60):
    """Tiles are generated off the request thread; wait for them to land."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with models.DBSession() as session:
            count = session.scalar(
                sa.text(
                    "SELECT count(*) FROM localizationtiles WHERE localization_id = :i"
                ),
                {"i": localization_id},
            )
        if count:
            return count
        time.sleep(1)
    return 0


def _localization(dateobs, name):
    with models.DBSession() as session:
        return session.scalar(
            sa.select(Localization).where(
                Localization.dateobs == dateobs, Localization.localization_name == name
            )
        )


def test_cone_containment_is_exact(super_admin_token, public_group2):
    """A cone localization resolves membership analytically."""
    dateobs = _unique_dateobs()
    ra, dec, error = 42.0, 12.0, 0.5
    payload = {
        "dateobs": dateobs.isoformat(),
        "trigger_id": f"EP{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": ra, "dec": dec, "error": error},
        "tags": ["EP"],
        "group_ids": [public_group2.id],
    }
    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    name = f"{ra:.5f}_{dec:.5f}_{error:.5f}"
    localization = _localization(dateobs, name)
    assert localization is not None

    # The name carries 1 sigma; the search cone must cover the credible level
    # being searched, not that sigma, or matches are dropped before containment
    # ever sees them.
    cone_ra, cone_dec, cone_radius = search_cone(
        localization, max_radius_deg=5.0, credible_level=90
    )
    assert (cone_ra, cone_dec) == (ra, dec)
    assert cone_radius == pytest.approx(error * gaussian_sigmas_for(0.9), rel=1e-6)

    positions = [
        (ra, dec),  # centre -> in
        (ra, dec + error * 0.5),  # comfortably inside
        (ra, dec + error * 2),  # 2 sigma: inside a 95% region
        (ra + 30.0, dec),  # far away
    ]

    async def run(cumprob):
        async with models.async_plain_session_factory() as session:
            return await contained_in_localization(
                session, localization, positions, cumprob=cumprob
            )

    # cumprob is honoured rather than ignored: 2 sigma holds ~86% of the
    # probability, so it is in at 95% and out at 50%.
    assert asyncio.run(run(0.95)) == {0, 1, 2}
    assert asyncio.run(run(0.5)) == {0, 1}


def test_cone_credible_levels_rank_by_depth(super_admin_token, public_group2):
    """A cone reports how deep inside each match sits, not just in/out.

    ``from_cone`` lays down a Gaussian of sigma = the error radius, so the
    enclosed probability at r is 1 - exp(-r^2 / 2 sigma^2). The centre is ~0,
    and the quoted radius (1 sigma) encloses ~39%.
    """
    dateobs = _unique_dateobs()
    ra, dec, error = 42.0, 12.0, 0.5
    payload = {
        "dateobs": dateobs.isoformat(),
        "trigger_id": f"EP{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": ra, "dec": dec, "error": error},
        "tags": ["EP"],
        "group_ids": [public_group2.id],
    }
    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    localization = _localization(dateobs, f"{ra:.5f}_{dec:.5f}_{error:.5f}")
    assert localization is not None

    positions = [
        (ra, dec),  # centre
        (ra, dec + error * 0.5),  # half a sigma out
        (ra, dec + error * 3),  # 3 sigma: outside even a 95% region
    ]

    async def run():
        async with models.async_plain_session_factory() as session:
            return await credible_levels_in_localization(
                session, localization, positions, cumprob=0.95
            )

    levels = asyncio.run(run())

    assert set(levels) == {0, 1}, levels
    assert levels[0] == 0.0
    assert levels[0] < levels[1], "the centre must rank ahead of an offset match"
    assert levels[1] == pytest.approx(1 - np.exp(-0.125), abs=1e-4)


def test_skymap_containment_uses_localization_tiles(super_admin_token, public_group2):
    """A non-cone localization resolves membership against its HEALPix tiles.

    A polygon skymap gives a localization whose name does not parse as a cone,
    so this drives the SQL containment path rather than the analytic one.
    """
    dateobs = _unique_dateobs()
    name = str(uuid.uuid4())
    # a ~4 deg box; vertices are (ra, dec)
    ra0, dec0 = 100.0, 10.0
    polygon = [
        (ra0 - 2.0, dec0 - 2.0),
        (ra0 + 2.0, dec0 - 2.0),
        (ra0 + 2.0, dec0 + 2.0),
        (ra0 - 2.0, dec0 + 2.0),
    ]
    payload = {
        "dateobs": dateobs.isoformat(),
        "skymap": {"polygon": polygon, "localization_name": name},
        "tags": ["TEST"],
        "group_ids": [public_group2.id],
    }
    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    localization = _localization(dateobs, name)
    assert localization is not None
    assert _wait_for_tiles(localization.id) > 0, "no localization tiles were generated"

    # the name is not a cone, so this must not take the analytic path
    from skyportal.utils.crossmatch import cone_from_localization_name

    assert cone_from_localization_name(name) is None

    positions = [
        (ra0, dec0),  # inside the box
        (ra0 + 40.0, dec0),  # far outside
        (ra0, dec0 + 40.0),  # far outside
    ]

    async def run(cumprob):
        async with models.async_plain_session_factory() as session:
            return await contained_in_localization(
                session, localization, positions, cumprob=cumprob
            )

    # Over the whole map, the interior point is contained and the far ones are
    # not -- this is what exercises the HEALPix conversion and the tile join.
    inside_full = asyncio.run(run(1.0))
    assert 0 in inside_full, f"interior point should be contained, got {inside_full}"
    assert 1 not in inside_full and 2 not in inside_full, (
        f"far positions leaked in: {inside_full}"
    )

    # A credible cut must never *add* positions. Note the interior point is not
    # asserted here: a polygon skymap is uniform, so every tile has the same
    # probdensity, the ordering that defines the 95% region is an arbitrary
    # tie-break, and an arbitrary 5% of the box falls outside it. That is the
    # real meaning of a credible region on a flat map -- there is no peak to be
    # near -- and the localizationDateobs source query behaves the same way.
    inside_95 = asyncio.run(run(0.95))
    assert inside_95 <= inside_full, (inside_95, inside_full)
    assert 1 not in inside_95 and 2 not in inside_95, (
        f"far positions leaked in at cumprob=0.95: {inside_95}"
    )


def test_containment_of_empty_input_is_empty(super_admin_token, public_group2):
    """No positions in, no indices out -- and no query issued."""

    async def run():
        async with models.async_plain_session_factory() as session:
            return await contained_in_localization(session, None, [])

    assert asyncio.run(run()) == set()
