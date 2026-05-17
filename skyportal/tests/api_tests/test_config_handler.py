from skyportal.tests import api

# Keys the ConfigHandler advertises in its docstring schema. If the handler
# ever drops one of these, this test should catch it.
_REQUIRED_KEYS = {
    "slackPreamble",
    "invitationsEnabled",
    "cosmology",
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
    status, data = api("GET", "config", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    cfg = data["data"]
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


def test_config_requires_authentication():
    """The endpoint is gated by auth_or_token."""
    status, _ = api("GET", "config")  # no token
    assert status == 401
