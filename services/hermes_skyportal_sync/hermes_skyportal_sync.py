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
from baselayer.app.flow import Flow
from baselayer.app.models import init_db, session_context_id
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    Group,
    Instrument,
    Obj,
    PhotometricSeries,
    Photometry,
    Source,
    Stream,
    User,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("hermes_sync")


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

    Returns
    -------
    obj : Obj
        The Obj instance (existing or newly created)
    created : bool
        True if a new Obj was created, False if it already existed
    """
    obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))

    if obj is None:
        obj = Obj(id=obj_id, ra=ra, dec=dec)
        session.add(obj)
        session.flush()
        log(f"Created new Obj: {obj_id}")
        return obj, True
    else:
        return obj, False


def build_instrument_mapping(session, tns_ids: list[int]):
    """Build a mapping from instrument names to database IDs based on TNS IDs.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session
    tns_ids : list[int]
        List of TNS IDs to include

    Returns
    -------
    mapping : dict[str, int]
        Dictionary mapping instrument names to database IDs
    missing_tns_ids : list[int]
        List of TNS IDs that were not found in the database
    """
    if not tns_ids:
        return {}, []

    instruments = session.scalars(
        sa.select(Instrument).where(Instrument.tns_id.in_(tns_ids))
    ).all()

    mapping = {inst.name: inst.id for inst in instruments}
    found_tns_ids = {inst.tns_id for inst in instruments}
    missing_tns_ids = [tns_id for tns_id in tns_ids if tns_id not in found_tns_ids]

    return mapping, missing_tns_ids


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

    Returns
    -------
    sources_created : int
        Number of new Source associations created
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

    return sources_created


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
            round(p.mjd, 7),
            p.filter,
            round(p.flux, 5) if p.flux is not None else None,
            round(p.fluxerr, 5)
            if p.fluxerr is not None and not np.isnan(p.fluxerr)
            else None,
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
        mjd = round(jd - 2400000.5, 7)

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
            round(flux, 5) if flux is not None else None,
            round(fluxerr, 5)
            if fluxerr is not None and not np.isnan(fluxerr)
            else None,
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
        instrument_mapping: dict[str, int] = None,
        bot_user_id: int = 1,
    ):
        self.default_group_ids = default_group_ids or []
        self.instrument_mapping = instrument_mapping or {}
        self.bot_user_id = bot_user_id
        self.processed_sources = set()
        self.message_count = 0
        self.created_sources = 0
        self.errors = 0

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
        self.message_count += 1

        title = data.get("title", "No title")
        log(f"Processing message: {title}")

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

        log(f"  Target: {name}")
        log(f"    RA: {ra}")
        log(f"    Dec: {dec}")

        target_photometry = [p for p in photometry if p.get("target_name") == name]

        if target_photometry:
            instrument_counts = Counter(
                f"{p.get('telescope', 'Unknown')}/{p.get('instrument', 'Unknown')}"
                for p in target_photometry
            )

            for inst_key, count in sorted(instrument_counts.items()):
                log(f"      {inst_key}: {count} points")
        else:
            log("    No photometry data for this target")

        self.processed_sources.add(name)
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
            _, obj_created = create_or_get_obj(
                session, obj_id, target.get("ra"), target.get("dec")
            )

            if obj_created:
                self.created_sources += 1

            _ = create_source(session, obj_id, self.default_group_ids, self.bot_user_id)

            # Add photometry with deduplication
            if photometry:
                if not self.instrument_mapping:
                    log("    ✗ No instruments configured, skipping photometry")
                    return

                # Group photometry by instrument name
                phot_by_instrument = defaultdict(list)
                for point in photometry:
                    instrument_name = point.get("instrument")
                    if instrument_name:
                        phot_by_instrument[instrument_name].append(point)

                # Process photometry for each instrument
                for instrument_name, inst_phot in phot_by_instrument.items():
                    instrument_id = self.instrument_mapping.get(instrument_name)

                    if instrument_id is None:
                        log(
                            f"    ✗ Instrument '{instrument_name}' not in configured instruments, skipping {len(inst_phot)} points"
                        )
                        continue

                    added_count, duplicate_count = add_photometry_with_deduplication(
                        session,
                        obj_id,
                        inst_phot,
                        instrument_id,
                        self.default_group_ids,
                        self.bot_user_id,
                    )

                    skipped_count = len(inst_phot) - added_count - duplicate_count
                    log(
                        f"    → {instrument_name}: {added_count} added, {duplicate_count} duplicates skipped, {skipped_count} invalid/skipped"
                    )

            session.commit()
            log(f"    ✓ Successfully synced {obj_id}")

            if obj_created:
                try:
                    flow = Flow()
                    flow.push(
                        "*",
                        action_type="baselayer/SHOW_NOTIFICATION",
                        payload={
                            "note": f"New source {obj_id} synced from Hermes",
                            "type": "info",
                            "duration": 5000,
                        },
                    )
                except Exception:
                    pass

        except Exception as e:
            log(f"    ✗ Error syncing {obj_id} with SkyPortal: {e}")
            traceback.print_exc()
            session.rollback()
            self.errors += 1

            try:
                flow = Flow()
                flow.push(
                    "*",
                    action_type="baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f"Error syncing {obj_id} from Hermes: {str(e)}",
                        "type": "error",
                        "duration": 8000,
                    },
                )
            except Exception:
                pass


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
        instrument_mapping: dict[str, int] | None = None,
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
            instrument_mapping=instrument_mapping,
            bot_user_id=bot_user_id,
        )

        instrument_names = list(instrument_mapping.keys()) if instrument_mapping else []
        log(
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
        log(f"Topic: {self.topic}")
        log(f"Username: {self.username}")
        log(f"Read from start: {self.from_start}")
        log(f"Max age (days): {self.max_age_days}")

        self.consumer = self.build_consumer()
        self.consumer.subscribe([self.topic])
        log(f"Subscribed to {self.topic}")
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
                    log(f"Skipping old message (offset {msg.offset()})")
                    continue

                self._process_kafka_message(msg)

        except KeyboardInterrupt:
            log("Service interrupted")
        finally:
            self._cleanup()

    def _process_kafka_message(self, msg) -> None:
        """Process a single Kafka message with database session."""
        try:
            ts = msg.timestamp()[1]
            if ts > 0:
                msg_timestamp = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                log("=" * 60)
                log(f"Message timestamp: {msg_timestamp.isoformat()}")

            payload = msg.value()
            if not payload:
                log("Empty payload received")
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
    server_url = hermes_sync_cfg.get("kafka_server", "kafka.scimma.org")

    topic = cfg.get("app.hermes.topic", "skyportal.skyportal_test")

    # Service configuration
    from_start = hermes_sync_cfg.get("from_start", False)
    max_age_days = hermes_sync_cfg.get("max_age_days")
    bot_user_id = hermes_sync_cfg.get("bot_user_id", 1)
    group_ids = hermes_sync_cfg.get("group_ids", [1])
    instrument_tns_ids = hermes_sync_cfg.get("instrument_tns_ids", [])

    if not username or not password:
        log(
            "Hermes sync service is not configured. Please configure 'app.hermes.sync.scimma_username' and 'app.hermes.sync.scimma_password' in config.yaml to enable the service."
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
            instrument_mapping, missing_tns_ids = build_instrument_mapping(
                session, instrument_tns_ids
            )

            if missing_tns_ids:
                log(
                    f"Warning: Instruments with TNS IDs {missing_tns_ids} not found in database. "
                    f"Please create these instruments or remove them from 'app.hermes.sync.instrument_tns_ids' in config.yaml"
                )

            if instrument_mapping:
                log(f"Configured instruments: {list(instrument_mapping.keys())}")
            else:
                log(
                    "Warning: No instruments found for configured TNS IDs. Photometry will be skipped."
                )
        else:
            instrument_mapping = {}
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
        instrument_mapping=instrument_mapping,
        bot_user_id=bot_user_id,
    )

    sync_service.run()


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting Hermes sync service: {str(e)}")
        raise e
