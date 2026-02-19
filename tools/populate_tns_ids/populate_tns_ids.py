"""
Script to populate TNS IDs for instruments in SkyPortal.

This script maps SkyPortal instruments to their corresponding TNS API IDs
based on the data from https://www.wis-tns.org/api/get/values

The TNS instrument mappings are stored in tns_instruments.json.

Usage:
    PYTHONPATH=. python3 tools/populate_tns_ids/populate_tns_ids.py [--dry-run --config config.yaml]
"""

import argparse
import json
import sys
from pathlib import Path

import sqlalchemy as sa

from baselayer.app.env import load_env
from skyportal.models import DBSession, Instrument, init_db

DATA_FILE = Path(__file__).parent / "tns_instruments.json"


def load_tns_data():
    """
    Load TNS instrument data from JSON file.

    Returns:
        tuple: (tns_instruments dict, common_mappings dict)
    """
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"TNS data file not found: {DATA_FILE}")

    with open(DATA_FILE) as f:
        data = json.load(f)

    tns_instruments = {int(k): v for k, v in data["tns_instruments"].items()}
    common_mappings = data["common_mappings"]

    return tns_instruments, common_mappings


def find_tns_id_for_instrument(instrument_name, tns_instruments, common_mappings):
    """
    Try to find a TNS ID for a given instrument name.

    Args:
        instrument_name: Name of the instrument to look up
        tns_instruments: Dict mapping TNS ID to "Telescope - Instrument" name
        common_mappings: Dict mapping common instrument names to TNS IDs

    Returns:
        int or None: TNS ID if found, None otherwise
    """
    name_lower = instrument_name.lower().strip()
    if name_lower in common_mappings:
        return common_mappings[name_lower]
    for tns_id, tns_name in tns_instruments.items():
        if " - " in tns_name:
            _, inst_part = tns_name.split(" - ", 1)
            if inst_part.lower() == name_lower:
                return tns_id
            if name_lower in inst_part.lower() or inst_part.lower() in name_lower:
                return tns_id

    return None


def populate_tns_ids(dry_run=False):
    """
    Populate TNS IDs for instruments in the database.

    Args:
        dry_run: If True, only print what would be done without making changes
    """
    tns_instruments, common_mappings = load_tns_data()

    with DBSession() as session:
        instruments = session.scalars(sa.select(Instrument)).all()

        if not instruments:
            print("No instruments found in database.")
            return

        updated = 0
        not_found = 0
        already_set = 0

        print(f"\nFound {len(instruments)} instruments in database.")
        print("-" * 80)

        for instrument in instruments:
            if instrument.tns_id is not None:
                print(
                    f"✓ {instrument.name:<30} TNS ID already set: {instrument.tns_id}"
                )
                already_set += 1
                continue

            tns_id = find_tns_id_for_instrument(
                instrument.name, tns_instruments, common_mappings
            )

            if tns_id is not None:
                tns_name = tns_instruments.get(tns_id, "Unknown")
                if dry_run:
                    print(
                        f"→ {instrument.name:<30} Would set TNS ID: {tns_id} ({tns_name})"
                    )
                else:
                    instrument.tns_id = tns_id
                    print(f"✓ {instrument.name:<30} Set TNS ID: {tns_id} ({tns_name})")
                updated += 1
            else:
                print(
                    f"✗ {instrument.name:<30} No TNS ID found - manual mapping needed"
                )
                not_found += 1

        if not dry_run:
            session.commit()
            print("\n" + "=" * 80)
            print(f"Successfully updated {updated} instruments with TNS IDs.")
        else:
            print("\n" + "=" * 80)
            print(f"DRY RUN: Would update {updated} instruments with TNS IDs.")

        print(f"Already set: {already_set}")
        print(f"Not found: {not_found}")

        if not_found > 0:
            print("\nFor instruments without automatic mappings:")
            print(
                "1. Check the instrument name in TNS: https://www.wis-tns.org/api/get/values"
            )
            print(
                "2. Add the mapping to common_mappings in tools/populate_tns_ids/tns_instruments.json"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Populate TNS IDs for SkyPortal instruments"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--config",
        dest="config",
        default="config.yaml.defaults",
        help="Path to config file (default: config.yaml.defaults)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("SkyPortal Instrument TNS ID Population Script")
    print("=" * 80)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    # Load configuration and initialize database connection
    _, cfg = load_env()
    init_db(**cfg["database"])

    try:
        populate_tns_ids(dry_run=args.dry_run)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
