import os

import sqlalchemy as sa
from sqlalchemy.orm import joinedload
import time
import pandas as pd
import numpy as np
import requests
import yaml
from astropy.time import Time
from astropy.visualization import (
    AsymmetricPercentileInterval,
    LinearStretch,
    LogStretch,
    ImageNormalize,
)
import datetime
import gzip
import io
from astropy.io import fits
from matplotlib import pyplot as plt
import base64
import conesearch_alchemy as ca

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from fink_client.consumer import AlertConsumer
from fink_filters.classification import extract_fink_classification_from_pdf

from skyportal.handlers.api.source import post_source

from skyportal.models import (
    DBSession,
    Obj,
    Instrument,
    Group,
    Taxonomy,
    Stream,
    Filter,
    Candidate,
    GcnEvent,
    LocalizationTile,
    # UserNotification,
    # GroupUser,
    Galaxy,
)

from baselayer.app.models import User

env, cfg = load_env()
init_db(**cfg['database'])

log = make_log('fink')

REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']


def get_token():
    """
    Get token from .tokens.yaml

    Returns
    -------
    str
        Skyportal admin token
    """
    try:
        token = yaml.load(open('.tokens.yaml'), Loader=yaml.Loader)['INITIAL_ADMIN']
        return token
    except (FileNotFoundError, TypeError, KeyError):
        print('No token found')
        return None


def get_taxonomy():
    """
    Get fink taxonomy from taxonomy.yaml

    Returns
    -------
    dict
        taxonomy dictionary
    """
    try:
        taxonomy_dict = yaml.load(
            open('services/fink/data/taxonomy.yaml'), Loader=yaml.Loader
        )
        return taxonomy_dict
    except (FileNotFoundError, TypeError, KeyError):
        print('No taxonomy found')
        return None


def is_loaded():
    """
    Check if SkyPortal is ready to receive requests

    Returns
    -------
    bool
        True if ready, False otherwise
    """
    port = cfg['ports.app_internal']
    try:
        r = requests.get(
            f'http://localhost:{port}/api/sysinfo', timeout=REQUEST_TIMEOUT_SECONDS
        )
    except:  # noqa: E722
        status_code = 0
    else:
        status_code = r.status_code

    if status_code == 200:
        return True
    else:
        return False


def fink_actived():
    """
    Check if Fink service is activated

    Returns
    -------
    bool
        True if activated, False otherwise
    """
    activated = True
    try:
        fink_cfg = cfg['fink']
        if fink_cfg is None or (not isinstance(fink_cfg, dict)) or fink_cfg == {}:
            activated = False
    except KeyError:
        activated = False
    return activated


def service():
    """
    Fink service

    Returns
    -------
    None
    """

    if not fink_actived():
        log('Fink service is not activated (missing configuration)')
        return

    while True:
        token = get_token()
        if is_loaded() and token is not None:
            try:
                poll_fink_alerts(token)
            except Exception as e:
                log(e)
        time.sleep(10)


def api_skyportal(method: str, endpoint: str, data=None, token=None):
    """
    Make an API call to a SkyPortal instance

    Arguments
    ---------
    method: str
        HTTP method
    endpoint: str
        API endpoint
    data: dict
        Data to send
    token: str
        SkyPortal token

    Returns
    -------
    response: requests.Response
        Response from SkyPortal
    """
    method = method.lower()

    if endpoint is None:
        raise ValueError("Endpoint not specified")
    if method not in ["head", "get", "post", "put", "patch", "delete"]:
        raise ValueError(f"Unsupported method: {method}")

    if method == "get":
        response = requests.request(
            method,
            f"{'https' if cfg['server']['ssl'] else 'http'}://"
            f"{cfg['server']['host']}:{cfg['server']['port']}"
            f"{endpoint}",
            params=data,
            headers={"Authorization": f"token {token}"},
        )
    else:
        response = requests.request(
            method,
            f"{'https' if cfg['server']['ssl'] else 'http'}://"
            f"{cfg['server']['host']}:{cfg['server']['port']}"
            f"{endpoint}",
            json=data,
            headers={"Authorization": f"token {token}"},
        )

    return response


def make_photometry(alert: dict, jd_start: float = None):
    """
    Make a de-duplicated pandas.DataFrame with photometry of alert['objectId'], from https://github.com/skyportal/kowalski

    Arguments
    ---------
    alert: dict
        Alert data
    jd_start: float
        Start time in JD to select photometry from

    Returns
    -------
    df_light_curve: pandas.DataFrame
        Light curve with deduplicated photometry in flux
    """
    df_candidate = pd.DataFrame(alert["candidate"], index=[0])

    df_prv_candidates = pd.DataFrame(alert["prv_candidates"])
    df_light_curve = pd.concat(
        [df_candidate, df_prv_candidates], ignore_index=True, sort=False
    )

    ztf_filters = {1: "ztfg", 2: "ztfr", 3: "ztfi"}
    df_light_curve["filter"] = df_light_curve["fid"].apply(lambda x: ztf_filters[x])

    df_light_curve["magsys"] = "ab"
    df_light_curve["mjd"] = df_light_curve["jd"] - 2400000.5

    df_light_curve["mjd"] = df_light_curve["mjd"].apply(lambda x: np.float64(x))
    df_light_curve["magpsf"] = df_light_curve["magpsf"].apply(lambda x: np.float32(x))
    df_light_curve["sigmapsf"] = df_light_curve["sigmapsf"].apply(
        lambda x: np.float32(x)
    )

    df_light_curve = (
        df_light_curve.drop_duplicates(subset=["mjd", "magpsf"])
        .reset_index(drop=True)
        .sort_values(by=["mjd"])
    )

    # filter out bad data:
    mask_good_diffmaglim = df_light_curve["diffmaglim"] > 0
    df_light_curve = df_light_curve.loc[mask_good_diffmaglim]

    # convert from mag to flux

    # step 1: calculate the coefficient that determines whether the
    # flux should be negative or positive
    coeff = df_light_curve["isdiffpos"].apply(
        lambda x: 1.0 if x in [True, 1, "y", "Y", "t", "1"] else -1.0
    )

    # step 2: calculate the flux normalized to an arbitrary AB zeropoint of
    # 23.9 (results in flux in uJy)
    df_light_curve["flux"] = coeff * 10 ** (-0.4 * (df_light_curve["magpsf"] - 23.9))

    # step 3: separate detections from non detections
    detected = np.isfinite(df_light_curve["magpsf"])
    undetected = ~detected

    # step 4: calculate the flux error
    df_light_curve["fluxerr"] = None  # initialize the column

    # step 4a: calculate fluxerr for detections using sigmapsf
    df_light_curve.loc[detected, "fluxerr"] = np.abs(
        df_light_curve.loc[detected, "sigmapsf"]
        * df_light_curve.loc[detected, "flux"]
        * np.log(10)
        / 2.5
    )

    # step 4b: calculate fluxerr for non detections using diffmaglim
    df_light_curve.loc[undetected, "fluxerr"] = (
        10 ** (-0.4 * (df_light_curve.loc[undetected, "diffmaglim"] - 23.9)) / 5.0
    )  # as diffmaglim is the 5-sigma depth

    # step 5: set the zeropoint and magnitude system
    df_light_curve["zp"] = 23.9
    df_light_curve["zpsys"] = "ab"

    # only "new" photometry requested?
    if jd_start is not None:
        w_after_jd = df_light_curve["jd"] > jd_start
        df_light_curve = df_light_curve.loc[w_after_jd]

    return df_light_curve


def post_annotation_to_skyportal(alert, session, user, group_ids, token, log):
    """
    Post annotations to SkyPortal

    Arguments
    ---------
    alert: dict
        Alert data
    session: sqlalchemy.orm.session.Session
        Database session
    user: baselayer.app.models.User
        The user to use to query the database
    group_ids: list
        List of group IDs
    token: str
        SkyPortal token
    log: logging.Logger
        Logger

    Returns
    -------
    bool
        True if successful, False otherwise
    """

    annotations = {
        "obj_id": alert["objectId"],
        "origin": "Fink Science",
        "data": {  # fink science data
            "cdsxmatch": alert["cdsxmatch"],
            "rf_snia_vs_nonia": alert["rf_snia_vs_nonia"],
            "snn_snia_vs_nonia": alert["snn_snia_vs_nonia"],
            "snn_sn_vs_all": alert["snn_sn_vs_all"],
            "microlensing": alert["mulens"],
            "asteroids": alert["roid"],
            "rf_kn_vs_nonkn": alert["rf_kn_vs_nonkn"],
            "nalerthist": alert["nalerthist"],
            # "ad_features": alert["lc_*"],
            # "rf_agn_vs_nonagn": alert["rf_agn_vs_nonagn"],
        },
        "group_ids": group_ids,
    }

    # HOST GALAXY
    name, catalog, distmpc, distmpc_unc, distance_from_host = get_obj_host_galaxy(
        alert, session, user, log
    )
    if name is not None:
        annotations["data"] = {
            **annotations["data"],
            "host_galaxy_name": name,
            "host_galaxy_catalog": catalog,
            "host_galaxy_distmpc": distmpc,
            "host_galaxy_distmpc_unc": distmpc_unc,
            "host_galaxy_distance_from_obj (arcsec)": distance_from_host,
        }

    response = api_skyportal(
        "GET", f"/api/sources/{alert['objectId']}/annotations", None, token
    )

    try:
        if response.status_code == 200:
            existing_annotations = {
                annotation["origin"]: {
                    "annotation_id": annotation["id"],
                    "author_id": annotation["author_id"],
                }
                for annotation in response.json()["data"]
            }
            if 'Fink Science' in existing_annotations:
                annotations['author_id'] = existing_annotations['Fink Science'][
                    'author_id'
                ]
                method = "PUT"
                endpoint = f"/api/sources/{alert['objectId']}/annotations/{existing_annotations['Fink Science']['annotation_id']}"
            else:
                method = "POST"
                endpoint = f"/api/sources/{alert['objectId']}/annotations"
            try:
                response = api_skyportal(
                    method,
                    endpoint,
                    annotations,
                    token,
                )
                if response.json()["status"] == "success":
                    log(f"Posted {alert['objectId']} annotation to SkyPortal")
                    return True
                else:
                    log(f"Failed to post {alert['objectId']} annotation to SkyPortal")
                    return False
            except Exception as e:
                log(
                    f"Failed to post annotation of {alert['objectId']} to group_ids: {', '.join([str(g) for g in group_ids])} with error {e}"
                )
                print(e)
                return False
        else:
            log(f"Failed to get existing annotations of {alert['objectId']}")
            return False
    except Exception as e:
        log(
            f"Failed to post annotation of {alert['objectId']} to group_ids: {', '.join([str(g) for g in group_ids])} with error {e}"
        )
        print(e)
        return False


def post_classification_to_skyportal(
    topic, alert, user_name, group_ids, taxonomy_id, token, log
):
    """
    Post classification to SkyPortal

    Arguments
    ---------
    topic: str
        Kafka topic
    alert: dict
        Alert data
    user_name: str
        User name
    group_ids: list
        List of group ids
    taxonomy_id: int
        Taxonomy id
    token: str
        SkyPortal token
    log: function
        Logging function

    Returns
    -------
    bool
        True if successful, False otherwise
    """

    alert_pd = pd.DataFrame([alert])
    alert_pd["tracklet"] = ""
    classification = extract_fink_classification_from_pdf(alert_pd)[0]
    probability = None

    if (
        topic
        in [
            "fink_kn_candidates_ztf",
            "fink_early_kn_candidates_ztf",
            "fink_rate_based_kn_candidates_ztf",
        ]
        and "kilonova" not in classification.lower()
    ):
        classification = "Kilonova candidate"
        probability = alert["rf_kn_vs_nonkn"]

    data = {
        "obj_id": alert["objectId"],
        "classification": classification,
        "author_name": "fink_client",
        "taxonomy_id": taxonomy_id,
        "group_ids": group_ids,
    }

    if probability is not None:
        data["probability"] = probability

    response = api_skyportal(
        "GET", f"/api/sources/{alert['objectId']}/classifications", None, token
    )

    try:
        if response.status_code == 200:
            classification_id = None
            author_id = None
            for classification in response.json()["data"]:
                if (
                    classification["author_name"] == user_name
                    and classification["taxonomy_id"] == taxonomy_id
                ):
                    classification_id = classification["id"]
                    author_id = classification["author_id"]
                    break

            if classification_id is not None and author_id is not None:
                data['author_id'] = author_id
                data['author_name'] = user_name
                method = "PUT"
                endpoint = f"/api/classification/{classification_id}"
            else:
                method = "POST"
                endpoint = "/api/classification"

            try:
                response = api_skyportal(
                    method,
                    endpoint,
                    data,
                    token,
                )
                if response.json()["status"] == "success":
                    log(f"Posted {alert['objectId']} classification to SkyPortal")
                    return True
                else:
                    log(
                        f"Failed to post {alert['objectId']} classification to SkyPortal"
                    )
                    return False
            except Exception as e:
                log(
                    f"Failed to post classification of {alert['objectId']} to group_ids: {', '.join([str(g) for g in group_ids])} with error {e}"
                )
                print(e)
                return False
        else:
            log(f"Failed to get existing classifications of {alert['objectId']}")
            return False
    except Exception as e:
        log(
            f"Failed to post classification of {alert['objectId']} to group_ids: {', '.join([str(g) for g in group_ids])} with error {e}"
        )
        print(e)
        return False


def post_cutouts_to_skyportal(alert, token, log):
    """
    Post cutouts to SkyPortal, from https://github.com/skyportal/kowalski

    Arguments
    ----------
    alert: dict
        Alert data
    token: str
        SkyPortal token
    log: logging.Logger
        Logger
    """

    for i, (skyportal_type, cutout_type) in enumerate(
        [("new", "Science"), ("ref", "Template"), ("sub", "Difference")]
    ):
        cutout_data = alert[f'cutout{cutout_type}']['stampData']
        with gzip.open(io.BytesIO(cutout_data), "rb") as f:
            with fits.open(io.BytesIO(f.read()), ignore_missing_simple=True) as hdu:
                image_data = hdu[0].data
        image_data = np.flipud(image_data)
        plt.close("all")
        fig = plt.figure()
        fig.set_size_inches(4, 4, forward=False)
        ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
        ax.set_axis_off()
        fig.add_axes(ax)

        # replace nans with median:
        img = np.array(image_data)
        # replace dubiously large values
        xl = np.greater(np.abs(img), 1e20, where=~np.isnan(img))
        if img[xl].any():
            img[xl] = np.nan
        if np.isnan(img).any():
            median = float(np.nanmean(img.flatten()))
            img = np.nan_to_num(img, nan=median)

        norm = ImageNormalize(
            img,
            stretch=LinearStretch() if cutout_type == "Difference" else LogStretch(),
        )
        img_norm = norm(img)
        normalizer = AsymmetricPercentileInterval(
            lower_percentile=1, upper_percentile=100
        )
        vmin, vmax = normalizer.get_limits(img_norm)
        ax.imshow(img_norm, cmap="bone", origin="lower", vmin=vmin, vmax=vmax)
        buff = io.BytesIO()
        plt.savefig(buff, dpi=42, format="png")
        buff.seek(0)
        plt.close("all")

        thumbnail_dict = {
            "obj_id": alert["objectId"],
            "data": base64.b64encode(buff.read()).decode("utf-8"),
            "ttype": skyportal_type,
        }

        try:
            response = api_skyportal(
                "POST",
                "/api/thumbnail",
                thumbnail_dict,
                token,
            )
            if response.json()["status"] == "success":
                log(f"Posted {alert['objectId']} {skyportal_type} cutout to SkyPortal")
            else:
                log(
                    f"Failed to post {alert['objectId']} {skyportal_type} cutout to SkyPortal"
                )
        except Exception as e:
            log(
                f"Failed to post {alert['objectId']} {skyportal_type} cutout to SkyPortal"
            )
            print(e)


# TODO: move this to a more appropriate place where it can run for all alerts (not just fink's)
# it could be added as a DB trigger in the candidates or photometry models
# it would be triggered we similar conditions as those used for the photstats
def source_in_recent_gcns(alert, session, user, localization_cumprob, log):
    """
    Check if the source is in some of the recent GCNs (within 7 days)

    Arguments
    ---------
    alert: dict
        Alert data
    session: sqlalchemy.orm.session.Session
        Database session
    user: baselayer.app.models.User
        The user to use to query the database
    localization_cumprob: float
        Cumulative probability of the localization
    log: logging.Logger
        Logger

    Returns
    -------
    obj_in_events: list
        List of GcnEvent dateobs for which the source is in the localization
    """
    obj = session.scalars(Obj.select(user).where(Obj.id == alert["objectId"])).first()
    date_7_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    obj_in_events = []
    if obj is not None:
        if obj.photstats[-1].first_detected_mjd is not None:
            if obj.photstats[-1].first_detected_mjd >= Time(date_7_days_ago).mjd:
                gcn_events = session.scalars(
                    GcnEvent.select(user)
                    .where(GcnEvent.dateobs > date_7_days_ago)
                    .where(
                        GcnEvent.dateobs
                        < Time(
                            obj.photstats[-1].first_detected_mjd, format='mjd'
                        ).datetime
                    )
                ).all()
                if len(gcn_events) > 0:
                    for gcn_event in gcn_events:
                        # in gcnevents, we have a list of all its localizations, get the most recent one based on the value of created_at
                        localizations = gcn_event.localizations
                        localizations.sort(key=lambda x: x.created_at, reverse=True)
                        localization = localizations[0]
                        if localization is not None:
                            obj_query_options = []
                            obj_query_options.append(joinedload(Obj.photstats))
                            obj_query = Obj.select(user, columns=[Obj.id])
                            obj_query = Obj.select(
                                user, options=obj_query_options
                            ).where(Obj.id == alert["objectId"])
                            cum_prob = (
                                sa.func.sum(
                                    LocalizationTile.probdensity
                                    * LocalizationTile.healpix.area
                                )
                                .over(order_by=LocalizationTile.probdensity.desc())
                                .label('cum_prob')
                            )
                            localizationtile_subquery = (
                                sa.select(
                                    LocalizationTile.probdensity, cum_prob
                                ).filter(
                                    LocalizationTile.localization_id == localization.id
                                )
                            ).subquery()

                            min_probdensity = (
                                sa.select(
                                    sa.func.min(
                                        localizationtile_subquery.columns.probdensity
                                    )
                                ).filter(
                                    localizationtile_subquery.columns.cum_prob
                                    <= localization_cumprob
                                )
                            ).scalar_subquery()

                            tile_ids = session.scalars(
                                sa.select(LocalizationTile.id).where(
                                    LocalizationTile.localization_id == localization.id,
                                    LocalizationTile.probdensity >= min_probdensity,
                                )
                            ).all()

                            tiles_subquery = (
                                sa.select(Obj.id)
                                .filter(
                                    LocalizationTile.id.in_(tile_ids),
                                    LocalizationTile.healpix.contains(Obj.healpix),
                                )
                                .subquery()
                            )

                            obj_query = obj_query.join(
                                tiles_subquery,
                                Obj.id == tiles_subquery.c.id,
                            )

                            obj_in_loc = session.scalars(obj_query).first()
                            if obj_in_loc is not None:
                                log(f"Found {alert['objectId']} in {gcn_event.dateobs}")
                                obj_in_events.append(
                                    gcn_event.dateobs.strftime("%Y-%m-%dT%H:%M:%S")
                                )
    return obj_in_events


def distance(ra1, dec1, ra2, dec2):
    """
    Calculate the distance between two points on the sky

    Arguments
    ---------
    ra1: float
        The ra of the first point
    dec1: float
        The dec of the first point
    ra2: float
        The ra of the second point
    dec2: float
        The dec of the second point

    Returns
    -------
    d: float
        The distance between the two points in arcsec
    """

    # convert ra and dec to radians
    ra1 = np.radians(ra1)
    dec1 = np.radians(dec1)
    ra2 = np.radians(ra2)
    dec2 = np.radians(dec2)

    # calculate the distance
    d = (
        np.sin((dec1 - dec2) / 2) ** 2
        + np.cos(dec1) * np.cos(dec2) * np.sin((ra1 - ra2) / 2) ** 2
    )
    d = 2 * np.arcsin(np.sqrt(d))

    # convert to arcsec
    d = np.degrees(d) * 3600

    return d


def get_obj_host_galaxy(alert, session, user, log):
    """
    Arguments
    ---------
    alert: dict
        The alert packet
    session: sqlalchemy.orm.session.Session
        The database session
    user: baselayer.app.models.User
        The user to use to query the database
    log: function
        The log function to use to log messages

    Returns
    -------
    galaxy_name: str or None
        The name of the host galaxy
    galaxy_id: int or None
        The id of the host galaxy
    galaxy_distmpc: float or None
        The distance to the host galaxy in Mpc
    distance_to_galaxy: float or None
        The distance to the host galaxy in arcsec
    """
    obj = session.scalars(Obj.select(user).where(Obj.id == alert["objectId"])).first()
    if obj is not None:
        if obj.ra is not None and obj.dec is not None:
            point = ca.Point(ra=obj.ra, dec=obj.dec)
            radius = 1 / 3600.0
            max_radius = 10 / 3600.0
            while radius <= max_radius:
                galaxies = session.scalars(
                    Galaxy.select(user).where(Galaxy.within(point, radius))
                ).all()
                if len(galaxies) > 0:
                    galaxies.sort(key=lambda x: distance(x.ra, x.dec, obj.ra, obj.dec))
                    galaxy = galaxies[0]
                    log(f"Found {alert['objectId']} in {galaxy.name}")
                    return (
                        galaxy.name,
                        galaxy.id,
                        galaxy.distmpc,
                        galaxy.distmpc_unc,
                        distance(galaxy.ra, galaxy.dec, obj.ra, obj.dec),
                    )
                else:
                    radius += 1 / 3600.0
    return (None, None, None, None, None)


def init_consumer(
    fink_username: str = None,
    fink_password: str = None,
    fink_group_id: str = None,
    fink_servers: str = None,
    fink_topics: list = None,
    testing: bool = None,
    schema: str = None,
    log: callable = None,
):
    """
    Arguments
    ----------
    fink_username : str
        Fink username. Can be omitted, then the username is taken from the config file.
    fink_password : str
        Fink password. Can be omitted, then the password is taken from the config file.
    fink_group_id : int
        Fink group id. Can be omitted, then the group id is taken from the config file.
    fink_servers : list
        Fink servers. Can be omitted, then the servers are taken from the config file.
    fink_topics : list
        Fink topics. Can be omitted, then the topics are taken from the config file.
    testing : bool
        If True, we use the testing servers. Can be omitted, then the value is taken from the config file.
    schema : str
        Schema file. Can be omitted, then the schema is taken from the config file.
    log : function
        Log function. Can be omitted if you do not desire to log.
    Returns
    ----------
    consumer : AlertConsumer
        AlertConsumer object
    """

    fink_config = {
        "username": fink_username,
        "bootstrap.servers": fink_servers,
        "group_id": fink_group_id,
    }

    if fink_password is not None:
        fink_config["password"] = fink_password

    if (
        testing is True
    ):  # if in testing mode, we can use older alerts with a different schema than the one currently used by fink
        consumer = AlertConsumer(
            topics=fink_topics, config=fink_config, schema_path=schema
        )
    else:
        consumer = AlertConsumer(topics=fink_topics, config=fink_config)
    if log is not None:
        log(f"Fink topics you subscribed to: {fink_topics}")
    return consumer


def poll_alert(consumer: callable, max_timeout: int, log: callable = None):
    """
    Polls the consumer for an alert.
    Arguments
    ----------
        consumer : AlertConsumer
            AlertConsumer object
        maxtimeout : int
            Maximum time to wait for an alert
        log : function
            Log function. Can be omitted if you do not desire to log.
    Returns
    ----------
        alert : dict
            Alert object
    """
    try:
        # Poll the servers
        topic, alert, key = consumer.poll(max_timeout)
        if topic is None or alert is None:
            if log is not None:
                log(f"No alerts received in the last {max_timeout} seconds")
            return None, None
        else:
            return topic, alert
    except Exception as e:
        if log is not None:
            log(f"Error while polling: {e}")
        return None, None


def post_alert(
    topic: str = None,
    alert: dict = None,
    user_id: int = None,
    stream_id: int = None,
    filter_id: int = None,
    instrument_id: int = None,
    taxonomy_id: int = None,
    token: str = None,
    log: callable = None,
):
    """
    Posts an alert from Fink to SkyPortal.

    Arguments
    ----------
    topic: str
        Topic of the alert
    alert: dict
        Alert object
    user_id: int
        User id
    stream_id: int
        Stream id
    filter_id: int
        Filter id
    instrument_id: int
        Instrument id
    taxonomy_id: int
        Taxonomy id
    token: str
        SkyPortal token
    log: function
        Logger

    Returns
    ----------
    bool
        True if the alert was successfully posted, False otherwise
    """

    # check if the object already exists in the database
    with DBSession() as session:
        user = session.query(User).get(user_id)

        # FILTER ASSOCIATED TO TOPIC
        filters = session.scalars(
            Filter.select(user).where(
                Filter.name == topic, Filter.stream_id == stream_id
            )
        ).all()

        if filters is None:
            if log is not None:
                log(f"Filter {topic} not found in the database")
            return False

        filter_ids = [f.id for f in filters]

        # GROUPS ASSOCIATED TO FILTERS
        group_ids = [filter.group_id for filter in filters]

        # OBJECT
        obj = session.scalars(
            Obj.select(user).where(Obj.id == alert["objectId"])
        ).first()

        if obj is None:
            # create the object
            source = {
                'id': alert['objectId'],
                'ra': alert['candidate']['ra'],
                'dec': alert['candidate']['dec'],
            }
            post_source(source, user.id, session)

            post_cutouts_to_skyportal(alert, token, log)

        # CANDIDATE
        for filter_id in filter_ids:
            candidate = session.scalars(
                Candidate.select(user).where(
                    Candidate.passing_alert_id == alert['candidate']["candid"],
                    Candidate.obj_id == alert["objectId"],
                    Candidate.filter_id == filter_id,
                )
            ).first()

            if candidate is None:
                candidate = Candidate(
                    obj_id=alert["objectId"],
                    passing_alert_id=alert['candidate']["candid"],
                    passed_at=datetime.datetime.utcnow().strftime(
                        "%Y-%m-%dT%H:%M:%S.%f"
                    ),
                    uploader_id=user.id,
                    filter_id=filter_id,
                )
                session.add(candidate)
                session.commit()

        # PHOTOMETRY
        df_photometry = make_photometry(alert)
        df_photometry = df_photometry.fillna('')
        photometry = {
            "obj_id": alert["objectId"],
            "stream_ids": [stream_id],
            "instrument_id": instrument_id,
            "mjd": df_photometry["mjd"].tolist(),
            "flux": df_photometry["flux"].tolist(),
            "fluxerr": df_photometry["fluxerr"].tolist(),
            "zp": df_photometry["zp"].tolist(),
            "magsys": df_photometry["zpsys"].tolist(),
            "filter": df_photometry["filter"].tolist(),
            "ra": df_photometry["ra"].tolist(),
            "dec": df_photometry["dec"].tolist(),
        }

        if (len(photometry.get("flux", ())) > 0) or (
            len(photometry.get("fluxerr", ())) > 0
        ):
            try:
                response = api_skyportal("PUT", "/api/photometry", photometry, token)
                if response.json()["status"] == "success":
                    log(f"Posted {alert['objectId']} photometry to SkyPortal")
                else:
                    log(f"Failed to post {alert['objectId']} photometry to SkyPortal")
            except Exception as e:
                log(
                    f"Failed to post photometry of {alert['objectId']} to group_ids: {', '.join([str(g) for g in group_ids])}: {e}"
                )
                print(e)

            # ANNOTATIONS
            post_annotation_to_skyportal(alert, session, user, group_ids, token, log)

            # CLASSIFICATION
            post_classification_to_skyportal(
                topic,
                alert,
                user.username,
                group_ids,
                taxonomy_id,
                token,
                log,
            )

            # TODO: add this as a DB trigger later on
            # obj_in_events = source_in_recent_gcns(alert, session, user, 0.95, log)
            # if len(obj_in_events) > 0:
            #     group_users = session.scalars(
            #         GroupUser.select(user).where(GroupUser.group_id.in_(group_ids))
            #     ).all()
            #     for group_user in group_users:
            #         session.add(
            #             UserNotification(
            #                 user=group_user.user,
            #                 text=f"Object {alert['objectId']} was found in GCN event(s): {', '.join(obj_in_events)} (new alert)",
            #                 notification_type="obj_in_events",
            #                 url=f"/source/{alert['objectId']}",
            #             )
            #         )
            #     session.commit()


def poll_fink_alerts(token: str):
    """
    Poll Fink alerts and add necessary data to SkyPortal: (taxonomy, filters, streams, groups, etc.)

    Arguments
    ----------
    token: str
        The token to use to authenticate to SkyPortal.

    Returns
    ----------
    None
    """

    client_id = cfg['fink.client_id']
    client_secret = cfg['fink.client_secret']
    client_group_id = cfg.get('fink.client_group_id')
    topics = cfg['fink.topics']
    servers = cfg['fink.servers']
    maxtimeout = cfg.get('fink.maxtimeout', 10)
    testing = cfg.get('fink.testing', False)
    if testing is True:
        schema = cfg['fink.schema']
    else:
        schema = None

    if client_id is None or client_id == '':
        log('No client_id configured to poll fink alerts (config: fink.client_id)')
        return
    if topics is None or topics == '' or topics == []:
        log('No topics configured to poll fink alerts (config: fink.topics)')
        return
    if client_group_id is None or client_group_id == '':
        log(
            'No client_group_id configured to poll fink alerts (config: fink.client_group_id)'
        )
        return
    if servers is None or servers == '' or servers == []:
        log('No servers configured to poll fink alerts (config: fink.servers)')
        return
    if maxtimeout is None or maxtimeout == '':
        maxtimeout = 5

    if testing is True:
        if schema is not None or schema != '':
            try:
                schema = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), schema)
                )
                log(f"Using testing schema: {schema}")
            except Exception as e:
                log(f"Error while loading schema: {e}")
                return
        else:
            log(
                'No schema file configured to poll fink alerts in testing mode (config: fink.schema)'
            )
            return

    try:
        taxonomy_dict = get_taxonomy()
    except Exception as e:
        log(f"Couldn't open fink taxonomy: {e}")
        return

    try:
        with DBSession() as session:
            user = session.query(User).get(1)
            user_id = user.id
            instrument = session.scalars(
                Instrument.select(user).where(Instrument.name == "ZTF")
            ).first()
            if instrument is None:
                log("Could not find ZTF instrument in database")
                return
            instrument_id = instrument.id

            group = session.scalars(
                Group.select(user).where(Group.name == "Fink")
            ).first()
            if group is None:
                all_users = session.scalars(User.select(user)).all()
                group = Group(name="Fink", users=all_users)
                session.add(group)
                session.commit()
            group_id = group.id

            stream = session.scalars(
                Stream.select(user).where(Stream.name == "Fink")
            ).first()
            if stream is None:
                all_users = session.scalars(User.select(user)).all()
                stream = Stream(name="Fink")
                session.add(stream)
                session.commit()
            stream_id = stream.id

            filter_ids = []
            filters = session.scalars(
                Filter.select(user).where(Filter.stream_id == stream_id)
            ).all()
            if filters is None:
                filters = []
            if len(filters) == 0:
                for topic in topics:
                    filter = Filter(
                        stream_id=stream_id,
                        name=topic,
                        group_id=group_id,
                    )
                    session.add(filter)
                    session.commit()
                    filter_ids.append(filter.id)
            elif not all(
                topic in [filter.name for filter in filters] for topic in topics
            ):
                for topic in topics:
                    if not any(filter.name == topic for filter in filters):
                        filter = Filter(
                            stream_id=stream_id,
                            name=topic,
                            group_id=group_id,
                        )
                        session.add(filter)
                        session.commit()
                        filter_ids.append(filter.id)
            else:
                filter_ids = [filter.id for filter in filters]

            taxonomy = session.scalars(
                Taxonomy.select(user).where(Taxonomy.name == "Fink Taxonomy")
            ).first()
            if taxonomy is None:
                data = {
                    "name": taxonomy_dict['name'],
                    "hierarchy": taxonomy_dict['hierarchy'],
                    "version": taxonomy_dict['version'],
                }
                response = api_skyportal("POST", "/api/taxonomy", data, token)
                if response.json()["status"] == "success":
                    taxonomy_id = response.json()["data"]["taxonomy_id"]
                else:
                    log("Failed to post taxonomy to SkyPortal")
                    return
            else:
                taxonomy_id = taxonomy.id

    except Exception as e:
        log(f"Error getting user, instrument, groups, etc: {e}")
        return

    log('Starting fink service')

    try:
        consumer = init_consumer(
            fink_username=client_id,
            fink_password=client_secret,
            fink_group_id=client_group_id,
            fink_servers=servers,
            fink_topics=topics,
            testing=False,
            schema=schema,
            log=log,
        )

    except Exception as e:
        log(f'Error while initializing fink consumer: {e}')
        return

    while True:
        topic, alert = poll_alert(consumer, maxtimeout, log)
        if alert is not None:
            post_alert(
                topic,
                alert,
                user_id,
                stream_id,
                filter_ids,
                instrument_id,
                taxonomy_id,
                token,
                log,
            )


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f'Error: {e}')
