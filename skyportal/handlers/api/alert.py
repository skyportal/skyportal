# This is used by extensions of skyportal
# e.g., Fritz can overwrite this file
# and provide specific implementation
# for getting alerts.

alert_available = False


def post_alert(*args, **kwargs):
    pass


def get_alerts_by_position(*args, **kwargs):
    pass
