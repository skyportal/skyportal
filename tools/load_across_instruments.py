"""Load NASA ACROSS telescopes/instruments into SkyPortal.

Fetches the public ACROSS telescope + instrument registry and upserts matching
SkyPortal Telescope and Instrument records, tagging each Instrument with its
ACROSS UUID (`across_id`) so visibility queries can be routed to the ACROSS
calculator instead of the local astroplan airmass path. Idempotent; safe to
re-run. ACROSS facilities are ephemeris-propagated (spacecraft), so their
telescopes are created with `fixed_location=False`.

Duplicate handling (important for existing deployments like Fritz, which
already have Keck/Swift/etc.): existing telescopes are matched by normalized
name/nickname and reused. For instruments, a name match against an existing
record with no `across_id` is reported as a POTENTIAL DUPLICATE and left
untouched by default; pass --link-existing to instead set `across_id` on the
matched record rather than creating a new one. Always review the duplicates
report before running against production.

See https://across.sciencecloud.nasa.gov

Usage:
    python tools/load_across_instruments.py [--dry-run] [--link-existing]
"""

import argparse
import sys

import requests

from baselayer.app.env import load_env

env, cfg = load_env()

ACROSS_API_URL = (
    cfg.get("across.api_url") or "https://api.across.sciencecloud.nasa.gov/v1"
).rstrip("/")

# ACROSS-imported telescopes have no meaningful aperture; use a placeholder.
PLACEHOLDER_DIAMETER = 0.0


def classify_type(name: str) -> str:
    """Map an instrument name to a SkyPortal instrument type."""
    n = name.lower()
    is_spec = "spectrograph" in n or "spectrometer" in n or "grating" in n
    is_imager = "camera" in n or "imag" in n or "photometer" in n
    if is_spec and is_imager:
        return "imaging spectrograph"
    if is_spec:
        return "spectrograph"
    return "imager"


def _norm(s):
    return s.strip().lower() if s else ""


def fetch_across_telescopes():
    resp = requests.get(
        f"{ACROSS_API_URL}/telescope/",
        params={"include_filters": "false"},
        headers={"accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def run(dry_run: bool, link_existing: bool):
    telescopes = fetch_across_telescopes()
    n_inst = sum(len(t.get("instruments") or []) for t in telescopes)
    print(
        f"ACROSS returned {len(telescopes)} telescopes / {n_inst} instruments "
        f"from {ACROSS_API_URL}"
    )

    from baselayer.app.models import DBSession, init_db
    from skyportal.models import Instrument, Telescope

    init_db(**cfg["database"])
    session = DBSession()

    # Index existing records for duplicate detection.
    existing_tel = session.query(Telescope).all()
    tel_by_key = {}
    for t in existing_tel:
        for key in {_norm(t.name), _norm(t.nickname)}:
            if key:
                tel_by_key.setdefault(key, t)
    existing_inst = session.query(Instrument).all()
    inst_by_name = {_norm(i.name): i for i in existing_inst}
    inst_by_across = {i.across_id: i for i in existing_inst if i.across_id}

    created_tel = reused_tel = 0
    created_inst = linked_inst = updated_inst = 0
    duplicates = []  # (kind, across_name, existing_name)

    for t in telescopes:
        tel_name = t.get("name")
        short = t.get("short_name") or tel_name
        if not tel_name:
            continue

        telescope = tel_by_key.get(_norm(tel_name)) or tel_by_key.get(_norm(short))
        if telescope is None:
            telescope = Telescope(
                name=tel_name,
                nickname=short,
                diameter=PLACEHOLDER_DIAMETER,
                fixed_location=False,
                robotic=True,
            )
            session.add(telescope)
            session.flush()
            for key in {_norm(tel_name), _norm(short)}:
                if key:
                    tel_by_key[key] = telescope
            created_tel += 1
        else:
            reused_tel += 1
            if _norm(telescope.name) != _norm(tel_name):
                duplicates.append(("telescope", tel_name, telescope.name))

        for inst in t.get("instruments") or []:
            across_id = inst.get("id")
            inst_name = inst.get("name")
            short_name = inst.get("short_name")
            if not across_id or not inst_name:
                continue

            # Already imported (has this across_id) -> refresh telescope link.
            existing = inst_by_across.get(across_id)
            if existing is not None:
                existing.telescope_id = telescope.id
                updated_inst += 1
                continue

            # Name collision with a record that isn't ACROSS-backed yet.
            match = inst_by_name.get(_norm(inst_name)) or inst_by_name.get(
                _norm(short_name)
            )
            if match is not None and match.across_id is None:
                duplicates.append(("instrument", inst_name, match.name))
                if link_existing:
                    match.across_id = across_id
                    inst_by_across[across_id] = match
                    linked_inst += 1
                # else: leave the existing record untouched (report only)
                continue

            # Create a new instrument, disambiguating the unique name if needed.
            name = inst_name
            if _norm(name) in inst_by_name:
                name = f"{inst_name} ({short})"
            instrument = Instrument(
                name=name,
                type=classify_type(inst_name),
                telescope_id=telescope.id,
                across_id=across_id,
                filters=[],
            )
            session.add(instrument)
            inst_by_name[_norm(name)] = instrument
            inst_by_across[across_id] = instrument
            created_inst += 1

    if duplicates:
        print(f"\nPotential duplicates ({len(duplicates)}):")
        for kind, across_name, existing_name in duplicates:
            action = (
                "linked across_id"
                if (kind == "instrument" and link_existing)
                else (
                    "reused"
                    if kind == "telescope"
                    else "left untouched (use --link-existing to link)"
                )
            )
            print(
                f"  [{kind}] ACROSS '{across_name}' ~ existing '{existing_name}' -> {action}"
            )

    print(
        f"\nTelescopes: {created_tel} created, {reused_tel} reused. "
        f"Instruments: {created_inst} created, {linked_inst} linked, "
        f"{updated_inst} refreshed."
    )

    if dry_run:
        session.rollback()
        print("Dry run: rolled back, no database changes committed.")
    else:
        session.commit()
        print("Committed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the plan and print the duplicates report without committing.",
    )
    parser.add_argument(
        "--link-existing",
        action="store_true",
        help="Set across_id on an existing name-matched instrument instead of "
        "reporting it as a duplicate and skipping.",
    )
    args = parser.parse_args()
    try:
        run(args.dry_run, args.link_existing)
    except requests.RequestException as e:
        print(f"Failed to reach the ACROSS service: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
