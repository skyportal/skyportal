import datetime
import os
from pathlib import Path
import shutil
import pandas as pd
from requests.exceptions import ConnectionError

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import (init_db, Base, DBSession, Comment,
                              Instrument, Group, GroupUser, Photometry,
                              Source, Spectrum, Telescope, Thumbnail, User)
from skyportal.model_util import setup_permissions, load_demo_data


if __name__ == "__main__":
    """Insert test data"""
    env, cfg = load_env()
    load_demo_data(cfg)
