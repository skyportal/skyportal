"""Pre-fetch every registered sncosmo bandpass into the local cache.

Invoked from the Dockerfile so the image ships with all bandpass data already
on disk under SNCOSMO_DATA_DIR. Without this, the first app start has to
download each missing bandpass via astropy's 10s urlopen, and the cumulative
wait blocks the tornado workers long enough that nginx and the demo-data
loader give up with HTTP 503.

Individual failures (bandpasses whose CDN URL is dead, malformed metadata,
etc.) are logged and skipped — defensive bandpass loops in
skyportal/handlers/api/photometry.py already tolerate missing entries.
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

    # The Spanish Virtual Observatory host (svo2.cab.inta-csic.es) that hosts
    # several bandpass families (skymapper, gaia, etc.) is flaky enough that
    # a single sweep usually leaves ~20 of 183 bandpasses missing — and the
    # set of failures rotates between runs. Retry a few times so the slower
    # bandpasses get another shot. Each pass only re-tries the ones that
    # are still missing; cached ones return instantly.
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
