from . import FollowUpAPI


class VLAAPI(FollowUpAPI):
    """VLA Rubin Alert requests are completed in NRAO's form."""

    external_followup_form = {
        "type": "vla_rubin",
        "url": "https://docs.google.com/forms/d/e/1FAIpQLSdte3UOfF3NWaY-iMJlmumV0hDox5kpcgRxuHbHATgf64zk0w/viewform",
    }
