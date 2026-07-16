"""SkyPortal logging built on the standard library, replacing baselayer.log.

Keeps the `log = make_log(name)` convention, but returns a real
`logging.Logger` so call sites use `log.info(...)`, `log.error(...)`, etc.
"""

import logging
import sys

_configured = False


def setup_logging():
    """Send logging to stdout, once per process (supervisor captures it to log/)."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s %(name)s %(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.addHandler(handler)
    # Third-party loggers stay at WARNING; app loggers opt in to INFO via make_log
    root.setLevel(logging.WARNING)
    logging.captureWarnings(True)
    _configured = True


def make_log(name):
    """Return an INFO-level logger, configuring logging on first use."""
    setup_logging()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
