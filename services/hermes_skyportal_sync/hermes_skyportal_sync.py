"""
Hermes SkyPortal Synchronization Service

This service consumes source data from Hermes Kafka topic
and synchronizes it with SkyPortal by creating sources and uploading photometry.
"""

import json
import time
import traceback
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import sqlalchemy as sa
from confluent_kafka import Consumer

from baselayer.app.env import load_env
from baselayer.app.models import init_db, session_context_id
from baselayer.log import make_log
from skyportal.handlers.api.photometry import nan_to_none
from skyportal.models import (
    DBSession,
    Group,
    Instrument,
    Obj,
    PhotometricSeries,
    Photometry,
    Source,
    User,
)
from skyportal.utils.parse import safe_round
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("hermes_sync")
log_verbose = make_log("hermes_sync_verbose")


def create_or_get_obj(session, obj_id: str, ra: float, dec: float):
    """Create or retrieve an Obj from the database.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session
    obj_id : str
        Object ID
    ra : float
        Right ascension in degrees
    dec : float
        Declination in degrees
    """
    obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))

    if obj is None:
        obj = Obj(id=obj_id, ra=ra, dec=dec)
        session.add(obj)
        session.flush()
        log(f"Created new Obj: {obj_id}")


def build_instrument_mapping(session, tns_ids: list[int]):
    """Build mappings from instrument names and TNS IDs to database IDs.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session
    tns_ids : list[int]
        List of TNS IDs to include

    Returns
    -------
    name_mapping : dict[str, int]
        Dictionary mapping instrument names to database IDs
    tns_id_mapping : dict[int, int]
        Dictionary mapping instrument TNS IDs to database IDs
    missing_tns_ids : list[int]
        List of TNS IDs that were not found in the database
    """
    if not tns_ids:
        return {}, {}, []

    instruments = session.scalars(
        sa.select(Instrument).where(Instrument.tns_id.in_(tns_ids))
    ).all()

    name_mapping = {inst.name: inst.id for inst in instruments}
    tns_id_mapping = {inst.tns_id: inst.id for inst in instruments if inst.tns_id}
    found_tns_ids = {inst.tns_id for inst in instruments}
    missing_tns_ids = [tns_id for tns_id in tns_ids if tns_id not in found_tns_ids]

    return name_mapping, tns_id_mapping, missing_tns_ids


def create_source(session, obj_id: str, group_ids: list[int], user_id: int):
    """Create Source entries for an Obj if they don't exist.

    A Source is the association between an Obj and a Group.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session
    obj_id : str
        Object ID
    group_ids : list[int]
        List of group IDs to save the source to
    user_id : int
        User ID of the bot/user saving the source
    """
    sources_created = 0

    for group_id in group_ids:
        # Check if this source-group association already exists
        source = session.scalar(
            sa.select(Source).where(
                Source.obj_id == obj_id, Source.group_id == group_id
            )
        )

        if source is None:
            # Create new Source (saves Obj to Group)
            source = Source(
                obj_id=obj_id,
                group_id=group_id,
                saved_by_id=user_id,
                active=True,
            )
            session.add(source)
            sources_created += 1
            log(f"Created Source for {obj_id} in group {group_id}")

    if sources_created > 0:
        session.flush()


def add_photometry_with_deduplication(
    session,
    obj_id: str,
    photometry_data: list[dict[str, Any]],
    instrument_id: int,
    group_ids: list[int],
    user_id: int,
):
    """Add photometry points to an object with deduplication.

    Deduplication checks the following fields:
    - mjd (time)
    - filter (bandpass)
    - flux (measurement value)
    - fluxerr (measurement uncertainty)

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session
    obj_id : str
        Object ID
    photometry_data : list[dict]
        List of photometry dictionaries from Hermes
    instrument_id : int
        Instrument ID
    group_ids : list[int]
        List of group IDs to associate photometry with
    user_id : int
        User ID of the owner

    Returns
    -------
    added_count : int
        Number of new photometry points added
    duplicate_count : int
        Number of duplicate points skipped
    """
    if not photometry_data:
        return 0, 0

    added_count = 0
    duplicate_count = 0

    # Load existing photometry for this object and instrument
    existing_phot = session.scalars(
        sa.select(Photometry).where(
            Photometry.obj_id == obj_id, Photometry.instrument_id == instrument_id
        )
    ).all()

    # Create a set of existing (mjd, filter, flux, fluxerr) tuples for duplicate detection
    existing_keys = {
        (
            safe_round(p.mjd, 7),
            p.filter,
            safe_round(p.flux, 5),
            safe_round(nan_to_none(p.fluxerr), 5),
        )
        for p in existing_phot
    }

    groups = session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).all()

    for point in photometry_data:
        date_obs = point.get("date_obs")
        brightness = point.get("brightness")
        brightness_error = point.get("brightness_error")
        bandpass = point.get("bandpass")
        origin = point.get("origin")

        if date_obs is None or brightness is None or not bandpass:
            continue

        jd = float(date_obs)
        mjd = safe_round(jd - 2400000.5, 7)

        mag = float(brightness)
        flux = PhotometricSeries.mag2flux(np.array([mag]))[0]

        if brightness_error is not None:
            magerr = float(brightness_error)
            fluxerr = PhotometricSeries.magerr2fluxerr(
                np.array([mag]), np.array([magerr])
            )[0]
        else:
            fluxerr = np.nan

        # Check for duplicate : try to match mjd, filter, flux and fluxerr
        duplicate_key = (
            mjd,
            bandpass,
            safe_round(flux, 5),
            safe_round(nan_to_none(fluxerr), 5),
        )
        if duplicate_key in existing_keys:
            duplicate_count += 1
            continue

        altdata = {
            "imported_from": "hermes",
        }

        phot = Photometry(
            obj_id=obj_id,
            instrument_id=instrument_id,
            mjd=mjd,
            flux=flux,
            fluxerr=fluxerr,
            filter=bandpass,
            origin=origin,
            owner_id=user_id,
            altdata=altdata,
        )
        session.add(phot)

        for group in groups:
            if group not in phot.groups:
                phot.groups.append(group)

        added_count += 1
        existing_keys.add(duplicate_key)

    if added_count > 0:
        session.flush()

    return added_count, duplicate_count


class SourceProcessor:
    """Handles processing of astronomical source data from Kafka messages."""

    def __init__(
        self,
        default_group_ids: list[int] = None,
        instrument_name_mapping: dict[str, int] = None,
        instrument_tns_id_mapping: dict[int, int] = None,
        bot_user_id: int = 1,
    ):
        self.default_group_ids = default_group_ids or []
        self.instrument_name_mapping = instrument_name_mapping or {}
        self.instrument_tns_id_mapping = instrument_tns_id_mapping or {}
        self.bot_user_id = bot_user_id

    def process_message(self, session, data: dict[str, Any]) -> None:
        """Process a single Kafka message containing source data.
        A message may contain multiple targets but it's not the sharing service default method.

        Parameters
        ----------
        session : sqlalchemy.orm.Session
            Database session
        data : dict
            Kafka message data
        """
        title = data.get("title", "No title")
        log_verbose(f"Processing message: {title}")

        targets = data.get("data", {}).get("targets", [])
        photometry = data.get("data", {}).get("photometry", [])

        for target in targets:
            self._process_target(session, target, photometry)

    def _process_target(
        self, session, target: dict[str, Any], photometry: list[dict[str, Any]]
    ) -> None:
        """Process a single target.

        Parameters
        ----------
        session : sqlalchemy.orm.Session
            Database session
        target : dict
            Target dictionary from Hermes
        photometry : list[dict]
            List of photometry dictionaries
        """
        name = target.get("name")
        ra = target.get("ra")
        dec = target.get("dec")

        log_verbose(f"  Target: {name}")
        log_verbose(f"    RA: {ra}")
        log_verbose(f"    Dec: {dec}")

        target_photometry = [p for p in photometry if p.get("target_name") == name]

        if target_photometry:
            instrument_counts = Counter(
                f"{p.get('telescope', 'Unknown')}/{p.get('instrument', 'Unknown')}"
                for p in target_photometry
            )

            for inst_key, count in sorted(instrument_counts.items()):
                log_verbose(f"      {inst_key}: {count} points")
        else:
            log_verbose("    No photometry data for this target")

        self._sync_with_skyportal(session, name, target, target_photometry)

    def _sync_with_skyportal(
        self,
        session,
        obj_id: str,
        target: dict[str, Any],
        photometry: list[dict[str, Any]],
    ) -> None:
        """Synchronize source data with SkyPortal database.

        Parameters
        ----------
        session : sqlalchemy.orm.Session
            Database session
        obj_id : str
            Object ID
        target : dict
            Target dictionary from Hermes
        photometry : list[dict]
            List of photometry dictionaries
        """
        try:
            create_or_get_obj(session, obj_id, target.get("ra"), target.get("dec"))
            create_source(session, obj_id, self.default_group_ids, self.bot_user_id)

            # Add photometry with deduplication
            if photometry:
                if (
                    not self.instrument_name_mapping
                    and not self.instrument_tns_id_mapping
                ):
                    log_verbose("    ✗ No instruments configured, skipping photometry")
                    return

                # Group photometry by resolved instrument_id
                phot_by_instrument_id = defaultdict(list)
                unresolved_instruments = defaultdict(int)
                matched_by_tns_id = defaultdict(int)

                for point in photometry:
                    instrument_id = None
                    instrument_name = point.get("instrument")

                    # Try to extract instrument_tns_id from comments field
                    instrument_tns_id = None
                    comments = point.get("comments", "")
                    if "instrument_tns_id=" in comments:
                        try:
                            instrument_tns_id = int(
                                comments.split("instrument_tns_id=")[1].split()[0]
                            )
                        except (ValueError, IndexError):
                            pass

                    # see if TNS ID are available
                    if instrument_tns_id and self.instrument_tns_id_mapping:
                        instrument_id = self.instrument_tns_id_mapping.get(
                            instrument_tns_id
                        )
                        if instrument_id:
                            matched_by_tns_id[instrument_tns_id] += 1

                    # name matching
                    if instrument_id is None and instrument_name:
                        instrument_id = self.instrument_name_mapping.get(
                            instrument_name
                        )

                    if instrument_id:
                        phot_by_instrument_id[instrument_id].append(point)
                    else:
                        key = instrument_tns_id or instrument_name or "unknown"
                        unresolved_instruments[key] += 1

                for tns_id, count in matched_by_tns_id.items():
                    log_verbose(f"    Matched {count} points by TNS ID {tns_id}")

                for key, count in unresolved_instruments.items():
                    log_verbose(
                        f"    ✗ Instrument '{key}' not in configured instruments, skipping {count} points"
                    )

                for instrument_id, inst_phot in phot_by_instrument_id.items():
                    added_count, duplicate_count = add_photometry_with_deduplication(
                        session,
                        obj_id,
                        inst_phot,
                        instrument_id,
                        self.default_group_ids,
                        self.bot_user_id,
                    )

                    skipped_count = len(inst_phot) - added_count - duplicate_count
                    log_verbose(
                        f"    → instrument_id {instrument_id}: {added_count} added, {duplicate_count} duplicates skipped, {skipped_count} invalid/skipped"
                    )

            session.commit()
            log_verbose(f"    ✓ Successfully synced {obj_id}")

        except Exception as e:
            log(f"    ✗ Error syncing {obj_id} with SkyPortal: {e}")
            traceback.print_exc()
            session.rollback()


class HermesSyncService:
    """Main service for consuming Hermes messages and synchronizing with SkyPortal."""

    def __init__(
        self,
        username: str,
        password: str,
        server_url: str,
        topic: str,
        from_start: bool = False,
        max_age_days: float | None = None,
        group_ids: list[int] | None = None,
        instrument_name_mapping: dict[str, int] | None = None,
        instrument_tns_id_mapping: dict[int, int] | None = None,
        bot_user_id: int = 1,
    ):
        self.username = username
        self.password = password
        self.server_url = server_url
        self.topic = topic
        self.from_start = from_start
        self.max_age_days = max_age_days
        self.consumer = None

        self.processor = SourceProcessor(
            default_group_ids=group_ids or [],
            instrument_name_mapping=instrument_name_mapping,
            instrument_tns_id_mapping=instrument_tns_id_mapping,
            bot_user_id=bot_user_id,
        )

        instrument_names = (
            list(instrument_name_mapping.keys()) if instrument_name_mapping else []
        )
        log_verbose(
            f"Initialized Hermes sync service with bot_user_id={bot_user_id}, "
            f"group_ids={group_ids}, instruments={instrument_names}"
        )

    def build_consumer(self) -> Consumer:
        """Build and configure the Kafka consumer."""
        group_id = f"{self.username}-{self.topic}-monitor"
        if self.from_start:
            group_id += f"-{int(time.time())}"

        conf = {
            "bootstrap.servers": self.server_url,
            "group.id": group_id,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "SCRAM-SHA-512",
            "sasl.username": self.username,
            "sasl.password": self.password,
            "auto.offset.reset": "earliest",
            "enable.partition.eof": False,
            "log_level": 2,
        }
        return Consumer(conf)

    def is_too_old(self, ts_ms: int) -> bool:
        """Check if message is too old based on MAX_AGE_DAYS."""
        if self.max_age_days is None:
            return False

        msg_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        max_age = timedelta(days=self.max_age_days)
        return datetime.now(timezone.utc) - msg_dt > max_age

    def run(self) -> None:
        """Main monitoring loop."""
        log("Starting Hermes SkyPortal Synchronization Service")
        log_verbose(f"Username: {self.username}")
        log_verbose(f"Read from start: {self.from_start}")
        log_verbose(f"Max age (days): {self.max_age_days}")

        self.consumer = self.build_consumer()
        self.consumer.subscribe([self.topic])
        log_verbose(f"Subscribed to {self.topic}")
        log("Waiting for messages...")

        try:
            while True:
                msg = self.consumer.poll(1.0)  # 1 second timeout

                if msg is None:
                    continue

                if msg.error():
                    log(f"Kafka error: {msg.error()}")
                    continue

                ts = msg.timestamp()[1]
                if ts > 0 and self.is_too_old(ts):
                    log_verbose(f"Skipping old message (offset {msg.offset()})")
                    continue

                self._process_kafka_message(msg)

        finally:
            self._cleanup()

    def _process_kafka_message(self, msg) -> None:
        """Process a single Kafka message with database session."""
        try:
            ts = msg.timestamp()[1]
            if ts > 0:
                msg_timestamp = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                log_verbose("=" * 60)
                log_verbose(f"Message timestamp: {msg_timestamp.isoformat()}")

            payload = msg.value()
            if not payload:
                log_verbose("Empty payload received")
                return

            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                log(f"JSON parse error: {e}")
                log(f"Raw payload: {payload[:200]}...")
                return

            session_context_id.set(uuid.uuid4().hex)
            with DBSession() as session:
                try:
                    self.processor.process_message(session, data)
                except Exception as e:
                    log(f"Error processing message: {e}")
                    traceback.print_exc()
                    session.rollback()

        except Exception as e:
            log(f"Error in Kafka message handler: {e}")
            traceback.print_exc()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.consumer:
            self.consumer.close()
            log("Hermes sync service stopped")


@check_loaded(logger=log)
def service(*args, **kwargs):
    """Main service entry point with app loading check."""
    hermes_sync_cfg = cfg.get("app.hermes.sync", {})

    # Kafka/SCiMMA configuration
    username = hermes_sync_cfg.get("scimma_username")
    password = hermes_sync_cfg.get("scimma_password")
    server_url = hermes_sync_cfg.get("kafka_server")

    topic = cfg.get("app.hermes.topic")

    # Service configuration
    from_start = hermes_sync_cfg.get("from_start")
    max_age_days = hermes_sync_cfg.get("max_age_days")
    bot_user_id = hermes_sync_cfg.get("bot_user_id")
    group_ids = hermes_sync_cfg.get("group_ids")
    instrument_tns_ids = hermes_sync_cfg.get("instrument_tns_ids")

    required_configs = {
        "app.hermes.sync.scimma_username": username,
        "app.hermes.sync.scimma_password": password,
        "app.hermes.sync.kafka_server": server_url,
        "app.hermes.topic": topic,
        "app.hermes.sync.bot_user_id": bot_user_id,
        "app.hermes.sync.group_ids": group_ids,
    }

    missing = [name for name, value in required_configs.items() if not value]
    if missing:
        log(
            f"Missing required configuration: {', '.join(missing)}. "
            "Please configure these values in config.yaml"
        )
        return

    # Validate bot user and build instrument mapping
    with DBSession() as session:
        bot_user = session.scalar(sa.select(User).where(User.id == bot_user_id))
        if bot_user is None:
            log(
                f"Bot user with ID {bot_user_id} not found. Please create a bot user or configure 'bot_user_id' in config.yaml"
            )
            return
        log(f"Using bot user: {bot_user.username} (ID: {bot_user_id})")

        # Build instrument mapping from TNS IDs
        if instrument_tns_ids:
            instrument_name_mapping, instrument_tns_id_mapping, missing_tns_ids = (
                build_instrument_mapping(session, instrument_tns_ids)
            )

            if missing_tns_ids:
                log(
                    f"Warning: Instruments with TNS IDs {missing_tns_ids} not found in database. "
                )

            if instrument_name_mapping:
                log_verbose(
                    f"Configured instruments: {list(instrument_name_mapping.keys())}"
                )
            else:
                log(
                    "Warning: No instruments found for configured TNS IDs. Photometry will be skipped."
                )
        else:
            instrument_name_mapping = {}
            instrument_tns_id_mapping = {}
            log(
                "Warning: No instrument_tns_ids configured. Photometry will be skipped. "
                "Please configure 'app.hermes.sync.instrument_tns_ids' in config.yaml"
            )

    sync_service = HermesSyncService(
        username=username,
        password=password,
        server_url=server_url,
        topic=topic,
        from_start=from_start,
        max_age_days=max_age_days,
        group_ids=group_ids,
        instrument_name_mapping=instrument_name_mapping,
        instrument_tns_id_mapping=instrument_tns_id_mapping,
        bot_user_id=bot_user_id,
    )

    sync_service.run()


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting Hermes sync service: {str(e)}")
        raise e
