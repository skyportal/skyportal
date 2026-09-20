"""Ingest unverified X-ray transient candidates from the Einstein Probe data center.

This proprietary feed (https://ep.bao.ac.cn) is distinct from the public
``gcn.notices.einstein_probe.wxt.alert`` topic gcn_service already consumes: it
publishes earlier, keys on ``name`` + ``version``, and reports the observation
start rather than the trigger time, so the two streams produce separate
GcnEvents for the same transient, cross-linked through ``aliases``.

GcnEvent.read is group-scoped, so an event with no groups falls back to the
sitewide public group and publishes this invitation-only feed to everyone. The
service refuses to start unless ``einstein_probe.group_names`` is set.
"""

import asyncio
import time
import traceback
from datetime import datetime, timedelta

import requests
import sqlalchemy as sa

from baselayer.app import models
from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.gcn import post_gcnevent_from_dictionary
from skyportal.models import GcnProperty, Group, User
from skyportal.utils.naive_datetime import utcnow_naive
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("ep_service")

ep_cfg = cfg.get("einstein_probe", {}) or {}

user_id = 1

REQUIRED_FIELDS = [
    "name",
    "ra",
    "dec",
    "pos_err",
    "obs_start",
    "exp_time",
    "flux",
    "src_id",
    "src_significance",
    "bkg_counts",
    "net_counts",
    "net_rate",
    "version",
]

PROPERTY_FIELDS = [
    "exp_time",
    "flux",
    "src_id",
    "src_significance",
    "bkg_counts",
    "net_counts",
    "net_rate",
    "light_curve_url",
    "spectrum_url",
]

OBS_START_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class EPClient:
    """Client for the EP data center API; the token is minted on every fetch, never cached."""

    def __init__(self, base_url, email, password, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout

    def get_token(self):
        response = requests.post(
            f"{self.base_url}/api/get_tokenp",
            json={"email": self.email, "password": self.password},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            raise ValueError("EP data center returned no token")
        return token

    def get_unverified_candidates(self):
        token = self.get_token()
        response = requests.get(
            f"{self.base_url}/data_center/api/unverified_candidates",
            headers={"tdic-token": token},
            params={"token": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            return response.json() or []
        except ValueError:
            return []


def parse_obs_start(obs_start):
    """Parse the data center's observation start into a naive UTC datetime."""
    if isinstance(obs_start, datetime):
        return obs_start.replace(tzinfo=None)
    return datetime.strptime(obs_start, OBS_START_FORMAT)


def to_gcn_payload(candidate, group_ids, radius_multiplier=1.0):
    if not group_ids:
        raise ValueError("EP events must be restricted to at least one group")

    name = str(candidate["name"])
    ra = float(candidate["ra"])
    dec = float(candidate["dec"])
    pos_err = float(candidate["pos_err"])

    return {
        "dateobs": parse_obs_start(candidate["obs_start"]).isoformat(),
        # Stable across versions: EP revises obs_start, so dateobs cannot be the identity.
        "trigger_id": name,
        "aliases": [f"EP#{name}"],
        "skymap": {"ra": ra, "dec": dec, "error": pos_err * float(radius_multiplier)},
        "tags": ["EP", "X-ray"],
        "properties": {
            **{f: candidate.get(f) for f in PROPERTY_FIELDS},
            # already_ingested() keys the dedup on ep_name/ep_version.
            "ep_name": name,
            "ep_version": str(candidate["version"]),
            "ra": ra,
            "dec": dec,
            "pos_err": pos_err,
        },
        "group_ids": list(group_ids),
    }


async def already_ingested(session, name, version):
    """post_gcnevent_from_dictionary appends rows unconditionally, so every cycle would duplicate."""
    return (
        await session.scalar(
            sa.select(GcnProperty.id)
            .where(GcnProperty.data["ep_name"].astext == str(name))
            .where(GcnProperty.data["ep_version"].astext == str(version))
            .limit(1)
        )
    ) is not None


async def resolve_group_ids(session, user, group_names):
    if not group_names:
        raise ValueError(
            "einstein_probe.group_names is empty; refusing to ingest the "
            "proprietary EP feed into the sitewide public group"
        )
    groups = (
        (await session.scalars(Group.select(user).where(Group.name.in_(group_names))))
        .unique()
        .all()
    )
    missing = set(group_names) - {g.name for g in groups}
    if missing:
        raise ValueError(
            f"einstein_probe.group_names not found in DB: {sorted(missing)}"
        )
    return [g.id for g in groups]


async def ingest_candidates(candidates, group_names, radius_multiplier, max_event_age):
    cutoff = utcnow_naive() - timedelta(days=float(max_event_age))
    ingested = 0

    async with models.async_plain_session_factory() as session:
        user = await session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            log(f"User {user_id} not found in DB, cannot ingest EP candidates")
            return 0
        session.user_or_token = user

        group_ids = await resolve_group_ids(session, user, group_names)

        for candidate in candidates:
            name = candidate.get("name")
            try:
                missing = [f for f in REQUIRED_FIELDS if candidate.get(f) is None]
                if missing:
                    log(f"Skipping EP candidate {name}: missing fields {missing}")
                    continue

                version = str(candidate["version"])
                if await already_ingested(session, name, version):
                    continue

                dateobs = parse_obs_start(candidate["obs_start"])
                if dateobs < cutoff:
                    log(
                        f"Skipping EP candidate {name} v{version}: obs_start "
                        f"{dateobs.isoformat()} is older than {max_event_age} days"
                    )
                    continue

                payload = to_gcn_payload(candidate, group_ids, radius_multiplier)
                await post_gcnevent_from_dictionary(
                    payload, user_id, session, asynchronous=False
                )
                log(f"Ingested EP candidate {name} v{version} (dateobs {dateobs})")
                ingested += 1
            except Exception as e:
                traceback.print_exc()
                log(f"Failed to ingest EP candidate {name}: {e}")

    return ingested


def is_configured():
    if not ep_cfg.get("enabled", False):
        log("Einstein Probe ingestion is disabled, skipping")
        return False
    if not ep_cfg.get("email") or not ep_cfg.get("password"):
        log("einstein_probe.email/password not configured, skipping")
        return False
    if not ep_cfg.get("group_names"):
        log(
            "einstein_probe.group_names is empty; refusing to ingest the "
            "proprietary EP feed into the sitewide public group"
        )
        return False
    return True


@check_loaded(logger=log)
def service(*args, **kwargs):
    client = EPClient(
        ep_cfg.get("base_url", "https://ep.bao.ac.cn/ep"),
        ep_cfg["email"],
        ep_cfg["password"],
    )
    poll_interval = float(ep_cfg.get("poll_interval", 300))
    group_names = list(ep_cfg["group_names"])
    radius_multiplier = float(ep_cfg.get("radius_multiplier", 1.0))
    max_event_age = float(ep_cfg.get("max_event_age", 31.0))

    log(f"Polling EP data center every {poll_interval:.0f}s for groups {group_names}")

    while True:
        try:
            candidates = client.get_unverified_candidates()
            if candidates:
                count = asyncio.run(
                    ingest_candidates(
                        candidates, group_names, radius_multiplier, max_event_age
                    )
                )
                if count:
                    log(f"Ingested {count} new EP candidate(s)")
        except Exception as e:
            traceback.print_exc()
            log(f"Failed to poll EP data center: {e}")

        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        if is_configured():
            service()
    except Exception as e:
        log(f"Error: {e}")
