"""Pre-fetch sncosmo bandpasses into the local cache so app startup is
network-free. Failures are skipped; downstream loops already tolerate them.
"""

import os
import sys

import sncosmo
from sncosmo.bandpasses import _BANDPASSES


def _warm(names: list[str]) -> list[str]:
    """Try to fetch each bandpass; return the names that failed."""
    still_failed: list[str] = []
    for name in names:
        try:
            sncosmo.get_bandpass(name)
        except Exception as e:
            print(f"  skip {name}: {e}", file=sys.stderr)
            still_failed.append(name)
    return still_failed


def main() -> None:
    # sncosmo refuses to download into a missing data dir; create it.
    data_dir = os.environ.get("SNCOSMO_DATA_DIR")
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
    metadata = _BANDPASSES.get_loaders_metadata()
    all_names = [m["name"] for m in metadata if m.get("name")]
    total = len(all_names)

    # SVO host is flaky; retry the misses since the failing set rotates.
    attempts = int(os.environ.get("SNCOSMO_WARM_ATTEMPTS", "5"))
    failed = list(all_names)
    for i in range(1, attempts + 1):
        if not failed:
            break
        print(f"Warming attempt {i}/{attempts}: {len(failed)} bandpass(es)")
        failed = _warm(failed)
    cached = total - len(failed)
    print(f"sncosmo warm-up done: {cached} cached, {len(failed)} skipped")


if __name__ == "__main__":
    main()
