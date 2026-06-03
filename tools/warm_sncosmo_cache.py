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


def main() -> None:
    # sncosmo refuses to download into a missing data dir; create it.
    data_dir = os.environ.get("SNCOSMO_DATA_DIR")
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
    metadata = _BANDPASSES.get_loaders_metadata()
    print(f"Warming {len(metadata)} sncosmo bandpass(es)")
    ok = 0
    fail = 0
    for entry in metadata:
        name = entry.get("name")
        if not name:
            continue
        try:
            sncosmo.get_bandpass(name)
            ok += 1
        except Exception as e:
            print(f"  skip {name}: {e}", file=sys.stderr)
            fail += 1
    print(f"sncosmo warm-up done: {ok} cached, {fail} skipped")


if __name__ == "__main__":
    main()
