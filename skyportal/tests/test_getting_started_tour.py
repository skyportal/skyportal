"""Staleness guard for the tours and feature announcements.

A tour silently breaks when a targeted element is renamed or removed, so assert
every ``data-testid`` target still exists somewhere in ``static/js``.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
STATIC_JS = REPO_ROOT / "static" / "js"
TOUR_FILES = [
    STATIC_JS / "components" / "widget" / "GettingStartedTour.ts",
    STATIC_JS / "components" / "PageTours.ts",
    STATIC_JS / "components" / "FeatureAnnouncements.ts",
]

_TARGET_RE = re.compile(r'\[data-testid="([^"]+)"\]')
_ATTR_RE = re.compile(r'data-testid="([^"]+)"')
# Some components take the id as a prop and render it as data-testid.
_PROP_RE = re.compile(r'testId:\s*"([^"]+)"')
_SRC_SUFFIXES = {".tsx", ".ts", ".jsx", ".js", ".template"}


def _tour_target_testids():
    targets = []
    for tour_file in TOUR_FILES:
        targets.extend(_TARGET_RE.findall(tour_file.read_text()))
    return targets


def _testids_used_in_static_js():
    """Every data-testid used in static/js, minus the tour configs themselves
    (whose selectors would satisfy the check trivially)."""
    used = set()
    for path in STATIC_JS.rglob("*"):
        if path.suffix not in _SRC_SUFFIXES or path in TOUR_FILES:
            continue
        text = path.read_text(errors="ignore")
        used.update(_ATTR_RE.findall(text))
        used.update(_PROP_RE.findall(text))
    return used


def test_getting_started_tour_targets_exist():
    targets = _tour_target_testids()
    assert targets, "No data-testid targets found in the tour configs"

    used = _testids_used_in_static_js()
    missing = sorted(t for t in targets if t not in used)
    assert not missing, (
        "Getting Started tour targets no longer exist in static/js (an element "
        f"was likely renamed or removed): {missing}. Update the tour steps or "
        "restore the data-testid."
    )
