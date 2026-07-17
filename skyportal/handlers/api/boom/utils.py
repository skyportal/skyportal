import base64
import functools
import gzip
import inspect
import io
import traceback
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy.io import fits
from astropy.visualization import (
    AsymmetricPercentileInterval,
    ImageNormalize,
    LinearStretch,
    LogStretch,
)
from scipy.ndimage import rotate

from baselayer.app.env import load_env
from baselayer.log import make_log

log = make_log("app/boom-utils")


# ── Shared thumbnail helpers ─────────────────────────────────────────────────
# Imported lazily to avoid a circular-import at module load time (post_thumbnail
# lives in handlers/api/thumbnail which ultimately imports app models).
async def _post_thumbnail(thumbnail_dict, user_id, session):
    from ..thumbnail import post_thumbnail

    await post_thumbnail(thumbnail_dict, user_id=user_id, session=session)


thumbnail_types = [
    ("cutoutScience", "new"),
    ("cutoutTemplate", "ref"),
    ("cutoutDifference", "sub"),
]


def decode_cutout(cutout_data, survey):
    """Decode a raw cutout payload into (data_array, header).

    Handles bytes/list/base64-string input and the survey-specific compression:
    LSST cutouts are uncompressed FITS; all others are gzip-compressed.
    """
    if isinstance(cutout_data, list):
        cutout_data = bytes(cutout_data)
    elif isinstance(cutout_data, str):
        cutout_data = base64.b64decode(cutout_data)
    if survey.upper() == "LSST":
        with fits.open(io.BytesIO(cutout_data), ignore_missing_simple=True) as hdu:
            return np.array(hdu[0].data), dict(hdu[0].header)
    else:
        with (
            gzip.open(io.BytesIO(cutout_data), "rb") as f,
            fits.open(io.BytesIO(f.read()), ignore_missing_simple=True) as hdu,
        ):
            return np.array(hdu[0].data), dict(hdu[0].header)


def orient_cutout(data_array, survey, header):
    """Rotate/flip a cutout array so that North is up and West is right."""
    if survey.upper() == "ZTF":
        return np.flipud(data_array)
    if survey.upper() == "LSST":
        rotpa = header.get("ROTPA")
        if rotpa is not None:
            try:
                return rotate(
                    data_array, -rotpa, reshape=True, order=1, mode="constant", cval=0.0
                )
            except Exception as e:
                log(f"Failed to rotate LSST cutout: {e}")
    return data_array


def clean_image_array(img):
    """Scrub sentinel infinity values and NaNs from a cutout pixel array."""
    xl = ~np.isnan(img) & (np.abs(img) > 1e20)
    if img[xl].any():
        img[xl] = np.nan
    if np.isnan(img).any():
        img = np.nan_to_num(img, nan=float(np.nanmean(img.flatten())))
    return img


def render_cutout_png(data_array, stretch, normalizer, cmap="bone"):
    """Normalize and render a 2D array to a PNG BytesIO buffer.

    `stretch` and `normalizer` are astropy.visualization instances.
    Returns a seeked-to-start BytesIO containing the PNG bytes.
    """
    img = clean_image_array(data_array)
    norm = ImageNormalize(img, stretch=stretch)
    img_norm = norm(img)
    vmin, vmax = normalizer.get_limits(img_norm)

    buff = io.BytesIO()
    fig, ax = plt.subplots(figsize=(4, 4))
    fig.subplots_adjust(0, 0, 1, 1)
    ax.set_axis_off()
    ax.imshow(img_norm, cmap=cmap, origin="lower", vmin=vmin, vmax=vmax)
    plt.savefig(buff, dpi=42, format="png")
    plt.close(fig)
    buff.seek(0)
    return buff


def make_thumbnail(obj_id, cutout_data, cutout_type, thumbnail_type, survey):
    data_array, header = decode_cutout(cutout_data, survey)
    data_array = orient_cutout(data_array, survey, header)

    stretch = LinearStretch() if cutout_type == "cutoutDifference" else LogStretch()
    normalizer = AsymmetricPercentileInterval(lower_percentile=1, upper_percentile=100)
    buff = render_cutout_png(data_array, stretch, normalizer, cmap="bone")

    return {
        "obj_id": obj_id,
        "data": base64.b64encode(buff.read()).decode("utf-8"),
        "ttype": thumbnail_type,
    }


async def add_thumbnails(alert, survey, session):
    for cutout_type, thumbnail_type in thumbnail_types:
        if cutout_type not in alert:
            log(f"Cutout key {cutout_type} not found in alert")
            continue
        try:
            thumbnail = make_thumbnail(
                alert["objectId"],
                alert[cutout_type],
                cutout_type,
                thumbnail_type,
                survey,
            )
        except Exception as e:
            traceback.print_exc()
            log(f"Failed to create thumbnail for cutout type {cutout_type}: {e}")
            continue
        await _post_thumbnail(thumbnail, user_id=1, session=session)


_, cfg = load_env()


def get_boom_url():
    try:
        ports_to_ignore = [443, 80]
        return f"{cfg['boom.protocol']}://{cfg['boom.host']}" + (
            f":{int(cfg['boom.port'])}"
            if (
                isinstance(cfg["boom.port"], int)
                and int(cfg["boom.port"]) not in ports_to_ignore
            )
            else ""
        )
    except Exception as e:
        log(f"Error getting Boom URL: {e}")
        return None


def get_boom_credentials():
    username = cfg.get("boom.username")
    password = cfg.get("boom.password")
    if username is None or password is None:
        log("Boom credentials not found in configuration")
        return None
    return {"username": username, "password": password}


boom_url = get_boom_url()
boom_credentials = get_boom_credentials()


def get_boom_token():
    try:
        if boom_url is None or boom_credentials is None:
            return None, None
        auth_url = f"{boom_url}/auth"
        current_time = datetime.utcnow()
        auth_response = requests.post(
            auth_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=boom_credentials,
        )
        auth_response.raise_for_status()
        data = auth_response.json()
        token = data["access_token"]
        expires_at = None
        if data.get("expires_in"):
            expires_in = int(data["expires_in"])
            expires_at = current_time + timedelta(seconds=expires_in)
        return token, expires_at
    except Exception as e:
        log(f"Error getting Boom token: {e}")
        return None, None


boom_token, boom_token_expires_at = get_boom_token()


def _refresh_boom_token():
    global boom_url
    global boom_credentials
    if boom_url is None or boom_credentials is None:
        raise ValueError("Boom is not available")
    global boom_token
    global boom_token_expires_at
    if boom_token is None or (
        boom_token_expires_at is not None
        and boom_token_expires_at < datetime.utcnow() + timedelta(seconds=1800)
    ):
        boom_token, boom_token_expires_at = get_boom_token()
    if boom_token is None:
        raise ValueError("Boom is not available")


def boom_available(func):
    # Preserve the coroutine-ness of async handlers so baselayer's
    # auth_or_token/permissions decorators take their async path.
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _refresh_boom_token()
            return await func(*args, **kwargs)

        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _refresh_boom_token()
        return func(*args, **kwargs)

    return wrapper


# JavaScript's Number.MAX_SAFE_INTEGER (2^53 - 1)
MAX_SAFE_INTEGER = 2**53 - 1


# def convert_large_ints(obj):
#     """Recursively convert integers that exceed JS Number.MAX_SAFE_INTEGER to strings.

#     JavaScript cannot represent integers larger than 2^53 - 1 without loss of
#     precision. This function walks the response tree and converts any
#     out-of-range integer to its string representation so the browser receives
#     the exact value.
#     """
#     if isinstance(obj, bool):
#         return obj
#     if isinstance(obj, int):
#         if obj > MAX_SAFE_INTEGER or obj < -MAX_SAFE_INTEGER:
#             return str(obj)
#         return obj
#     if isinstance(obj, dict):
#         return {k: convert_large_ints(v) for k, v in obj.items()}
#     if isinstance(obj, list):
#         return [convert_large_ints(item) for item in obj]
#     return obj


# let's take a different approach: we convert to int all key: value where value is a number and where key ends with "id" (case insensitive)
def convert_large_ints(obj):
    """Recursively convert numeric values of keys ending with 'id' to strings.

    This function walks the response tree and converts any numeric value of a key
    that ends with 'id' (case insensitive) to a string. This allows the
    frontend to receive these values as strings while still preserving precision
    for large IDs.
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if isinstance(v, int | float) and k.lower().endswith("id"):
                try:
                    new_obj[k] = str(int(v))
                except ValueError:
                    new_obj[k] = v
            else:
                new_obj[k] = convert_large_ints(v)
        return new_obj
    if isinstance(obj, list):
        return [convert_large_ints(item) for item in obj]
    return obj
