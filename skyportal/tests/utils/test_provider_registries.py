import subprocess
import sys

from skyportal import broker_apis, facility_apis


def test_facility_api_names_resolve():
    for name in facility_apis.API_CLASSNAMES + facility_apis.LISTENER_CLASSNAMES:
        assert getattr(facility_apis, name).__name__ == name


def test_broker_api_names_resolve():
    for name in broker_apis.BROKER_CLASSNAMES:
        assert getattr(broker_apis, name).__name__ == name


def test_importing_the_registries_is_cheap():
    heavy = ("pandas", "matplotlib.pyplot", "numba", "scipy")
    code = (
        "import sys, skyportal.broker_apis, skyportal.facility_apis;"
        f"print([m for m in {heavy} if m in sys.modules])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]", (
        f"a provider module is imported eagerly again: {result.stdout.strip()}"
    )
