"""Shared server-side cutout -> thumbnail rendering for broker providers.

Ported from fritz's BOOM utils: decode the survey's FITS cutout, orient it,
stretch/normalize, render to a PNG, and post it as an skyportal Thumbnail. Like
the save machinery this is survey-keyed, not broker-keyed.
"""

import base64
import gzip
import io

import matplotlib

matplotlib.use("Agg")  # headless, thread-safe rendering

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from astropy.io import fits  # noqa: E402
from astropy.visualization import (  # noqa: E402
    AsymmetricPercentileInterval,
    ImageNormalize,
    LinearStretch,
    LogStretch,
)
from scipy.ndimage import rotate  # noqa: E402

from baselayer.log import make_log  # noqa: E402

log = make_log("broker/thumbnails")

# (cutout field on the alert object) -> (skyportal thumbnail type)
THUMBNAIL_TYPES = [
    ("cutoutScience", "new"),
    ("cutoutTemplate", "ref"),
    ("cutoutDifference", "sub"),
]


def decode_cutout(cutout_data, survey):
    """Decode a raw cutout payload into (data_array, header). LSST cutouts are
    uncompressed FITS; all others are gzip-compressed."""
    if isinstance(cutout_data, list):
        cutout_data = bytes(cutout_data)
    elif isinstance(cutout_data, str):
        cutout_data = base64.b64decode(cutout_data)
    if survey.upper() == "LSST":
        with fits.open(io.BytesIO(cutout_data), ignore_missing_simple=True) as hdu:
            return np.array(hdu[0].data), dict(hdu[0].header)
    with (
        gzip.open(io.BytesIO(cutout_data), "rb") as f,
        fits.open(io.BytesIO(f.read()), ignore_missing_simple=True) as hdu,
    ):
        return np.array(hdu[0].data), dict(hdu[0].header)


def orient_cutout(data_array, survey, header):
    """Rotate/flip a cutout so North is up and West is right."""
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
    """Scrub sentinel infinities and NaNs from a cutout pixel array."""
    xl = ~np.isnan(img) & (np.abs(img) > 1e20)
    if img[xl].any():
        img[xl] = np.nan
    if np.isnan(img).any():
        img = np.nan_to_num(img, nan=float(np.nanmean(img.flatten())))
    return img


def render_cutout_png(data_array, stretch, normalizer, cmap="bone"):
    """Normalize and render a 2D array to PNG bytes (BytesIO, seeked to 0)."""
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


async def add_thumbnails(obj_id, cutouts, survey, session, user_id=1):
    """Render science/template/difference cutouts from ``cutouts`` (a dict with
    cutoutScience/Template/Difference FITS payloads) and post them as thumbnails.
    Best-effort: a failed cutout is logged and skipped, not fatal."""
    from ..handlers.api.thumbnail import post_thumbnail

    for cutout_type, thumbnail_type in THUMBNAIL_TYPES:
        cutout_data = (cutouts or {}).get(cutout_type)
        if not cutout_data:
            continue
        try:
            thumbnail = make_thumbnail(
                obj_id, cutout_data, cutout_type, thumbnail_type, survey
            )
            await post_thumbnail(thumbnail, user_id=user_id, session=session)
        except Exception as e:
            log(f"Failed to create thumbnail {thumbnail_type} for {obj_id}: {e}")
