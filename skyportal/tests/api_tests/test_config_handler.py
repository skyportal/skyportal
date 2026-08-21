import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client

# Keys the ConfigHandler advertises in its docstring schema. If the handler
# ever drops one of these, this test should catch it.
_REQUIRED_KEYS = {
    "slackPreamble",
    "invitationsEnabled",
    "cosmology",
    "cosmologyParams",
    "cosmoref",
    "allowedAllocationTypes",
    "allowedSpectrumTypes",
    "defaultSpectrumType",
    "gcnNoticeTypes",
    "gcnSummaryAcknowledgements",
    "maxNumDaysUsingLocalization",
    "allowedRecurringAPIMethods",
    "classificationsClasses",
    "tnsAllowedInstruments",
    "allowedInstrumentsForSharing",
    "gcnTagsClasses",
    "colorPalette",
    "bandpassesColors",
    "bandpassesWavelengths",
    "usePinecone",
    "usePhotometryValidation",
    "openai_summary_apikey_set",
    "openai_summary_parameters",
}


def test_config_returns_required_keys(view_only_token):
    """The /api/config endpoint exposes a known set of frontend-facing keys.

    Any authenticated user can read the config (it's frontend bootstrap
    data, not sensitive). This test pins the contract.
    """
    cfg = client(view_only_token).fetch_config()
    assert isinstance(cfg, dict)
    missing = _REQUIRED_KEYS - set(cfg)
    assert not missing, f"config missing keys: {sorted(missing)}"

    # Spot-check the types/shapes the frontend depends on.
    assert isinstance(cfg["invitationsEnabled"], bool)
    assert isinstance(cfg["colorPalette"], list) and cfg["colorPalette"]
    assert isinstance(cfg["bandpassesColors"], dict)
    assert isinstance(cfg["bandpassesWavelengths"], dict)
    # The OpenAI api key should never be exposed to the frontend.
    assert isinstance(cfg["openai_summary_apikey_set"], bool)
    assert "api_key" not in cfg["openai_summary_parameters"]


def test_config_cosmology_params_full_precision(view_only_token):
    """cosmologyParams exposes each parameter at full precision; astropy's repr
    rounds some values (e.g. H0 to 67.7 instead of 67.66)."""
    from skyportal.models import cosmo

    params = client(view_only_token).fetch_config()["cosmologyParams"]
    assert isinstance(params, list) and params
    assert all(set(row) == {"name", "value"} for row in params)

    by_name = {row["name"]: row["value"] for row in params}
    assert by_name["name"] == str(cosmo.name)
    # H0 shown exactly as used, not rounded by astropy's repr.
    assert by_name["H0"] == str(cosmo.H0)
    assert str(cosmo.H0.value) in by_name["H0"]


def test_config_requires_authentication():
    """The endpoint is gated by auth_or_token."""
    with pytest.raises(SkyPortalError) as err:
        client().fetch_config()  # no token
    assert err.value.status_code == 401
