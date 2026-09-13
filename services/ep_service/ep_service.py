"""Ingest unverified X-ray transient candidates from the Einstein Probe data center.

This is the proprietary EP feed (https://ep.bao.ac.cn), which is distinct from
the public ``gcn.notices.einstein_probe.wxt.alert`` topic that gcn_service
already consumes. The data center publishes candidates earlier and in more
detail, keyed by ``name`` + ``version``, and its ``obs_start`` is the
observation start rather than the trigger time -- so the two streams produce
separate GcnEvents for the same physical transient. The EP name is recorded in
``aliases`` so they can be cross-linked.

Because the feed is invitation-only, every event it creates is restricted to
the groups named in ``einstein_probe.group_names``. GcnEvent.read is
group-scoped, so an event with no groups would fall back to the sitewide public
group and publish the feed to every user; the service refuses to start rather
than let that happen.

The pure logic here -- ``to_gcn_payload`` and the dedup helpers -- is kept free
of module-level side effects so it can be exercised in tests without a poller
or network access.
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

user_id = 1

# Fields the data center must supply for a candidate to be ingestible. A
# candidate missing any of these is skipped with a warning rather than aborting
# the cycle -- one malformed record should not stall the whole feed.
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

# Numeric fields carried onto the GcnEvent as a GcnProperty.
PROPERTY_FIELDS = [
    "exp_time",
    "flux",
    "src_id",
    "src_significance",
    "bkg_counts",
    "net_counts",
    "net_rate",
    # EP-hosted data products for the candidate; present in the live feed and
    # worth keeping, since nothing else in skyportal can regenerate them.
    "light_curve_url",
    "spectrum_url",
]

OBS_START_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class EPClient:
    """Minimal client for the EP data center API.

    The token is short-lived and cheap to mint, so it is refreshed on every
    fetch rather than cached and invalidated.
    """

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
            candidates = response.json()
        except ValueError:
            return []
        return candidates or []


def parse_obs_start(obs_start):
    """Parse the data center's observation start into a naive UTC datetime."""
    if isinstance(obs_start, datetime):
        return obs_start.replace(tzinfo=None)
    return datetime.strptime(obs_start, OBS_START_FORMAT)


def validate_candidate(candidate):
    """Return the list of required fields missing from a candidate."""
    return [f for f in REQUIRED_FIELDS if candidate.get(f) is None]


def to_gcn_payload(candidate, group_ids, radius_multiplier=1.0):
    """Map an EP data-center candidate onto a post_gcnevent_from_dictionary payload.

    Parameters
    ----------
    candidate : dict
        One record from the unverified-candidate list.
    group_ids : list of int
        Groups the resulting GcnEvent is restricted to. Must be non-empty.
    radius_multiplier : float
        Scale factor on the EP position error when sizing the cone.

    Returns
    -------
    dict
    """
    if not group_ids:
        raise ValueError("EP events must be restricted to at least one group")

    name = str(candidate["name"])
    dateobs = parse_obs_start(candidate["obs_start"])
    error = float(candidate["pos_err"]) * float(radius_multiplier)

    properties = {f: candidate.get(f) for f in PROPERTY_FIELDS}
    # ep_name/ep_version are what the dedup check keys on, so they must live in
    # the property payload rather than only in the log.
    properties["ep_name"] = name
    properties["ep_version"] = str(candidate["version"])
    # the cone as EP reported it, so nothing downstream has to parse it back
    # out of the localization name
    properties["ra"] = float(candidate["ra"])
    properties["dec"] = float(candidate["dec"])
    properties["pos_err"] = float(candidate["pos_err"])

    return {
        "dateobs": dateobs.isoformat(),
        # identity across versions: EP may revise the position, and with it
        # obs_start, between versions of the same named candidate
        "trigger_id": name,
        "aliases": [f"EP#{name}"],
        "skymap": {
            "ra": float(candidate["ra"]),
            "dec": float(candidate["dec"]),
            "error": error,
        },
        "tags": ["EP", "X-ray"],
        "properties": properties,
        "group_ids": list(group_ids),
    }


async def already_ingested(session, name, version):
    """Whether this exact (name, version) has already been ingested.

    The poller re-fetches the entire unverified list every cycle, and
    post_gcnevent_from_dictionary appends GcnProperty and GcnTag rows
    unconditionally -- so without this guard every cycle would pile up
    duplicate rows on every event in the feed.
    """
    return (
        await session.scalar(
            sa.select(GcnProperty.id)
            .where(GcnProperty.data["ep_name"].astext == str(name))
            .where(GcnProperty.data["ep_version"].astext == str(version))
            .limit(1)
        )
    ) is not None


async def resolve_group_ids(session, user, group_names):
    """Resolve configured group names to ids, failing loudly if none match."""
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
    found = {g.name for g in groups}
    missing = set(group_names) - found
    if missing:
        raise ValueError(
            f"einstein_probe.group_names not found in DB: {sorted(missing)}"
        )
    return [g.id for g in groups]


async def ingest_candidates(candidates, group_names, radius_multiplier, max_event_age):
    """Ingest a batch of EP candidates, skipping duplicates and stale records."""
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
                missing = validate_candidate(candidate)
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
    ep_cfg = cfg.get("einstein_probe", {}) or {}
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
    if not is_configured():
        return

    ep_cfg = cfg["einstein_probe"]
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
            # The data center has unannounced maintenance windows; log and retry
            # on the next cycle rather than exiting.
            traceback.print_exc()
            log(f"Failed to poll EP data center: {e}")

        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error: {e}")
