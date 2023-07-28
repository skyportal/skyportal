from PIL import Image, ImageStat, UnidentifiedImageError
import requests
import gzip
import io
import base64
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.visualization import (
    ImageNormalize,
    LinearStretch,
    LogStretch,
    AsymmetricPercentileInterval,
)

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()

# Default classification parameters
thumb_size = cfg["image_grayscale_params.thumb_size"]
MSE_cutoff = cfg["image_grayscale_params.MSE_cutoff"]
adjust_color_bias = cfg["image_grayscale_params.adjust_color_bias"]

log = make_log('thumbnail')


def post_thumbnails(obj_ids, timeout=2):

    request_body = {'obj_ids': obj_ids}

    thumbnail_microservice_url = f'http://127.0.0.1:{cfg["ports.thumbnail_queue"]}'

    resp = requests.post(thumbnail_microservice_url, json=request_body, timeout=timeout)
    if resp.status_code != 200:
        log(f'Thumbnail request failed for {request_body["obj_id"]}: {resp.content}')


def image_is_grayscale(
    file,
    thumb_size=thumb_size,
    MSE_cutoff=MSE_cutoff,
    adjust_color_bias=adjust_color_bias,
):
    """
    Determine whether an image is colored or grayscale, roughly. That is, even if a PNG
    is encoded with RGB color type, if it is mostly black/white with very few colored pixels
    it will be labeled as grayscale by this function.

    Adapted from:
    https://stackoverflow.com/questions/20068945/detect-if-image-is-color-grayscale-or-black-and-white-with-python-pil
    """
    try:
        pil_img = Image.open(file)
    except UnidentifiedImageError:
        return False

    bands = pil_img.getbands()
    if bands == ('R', 'G', 'B') or bands == ('R', 'G', 'B', 'A'):
        thumb = pil_img.resize((thumb_size, thumb_size))
        SSE, bias = 0, [0, 0, 0]
        if adjust_color_bias:
            bias = ImageStat.Stat(thumb).mean[:3]
            bias = [b - sum(bias) / 3 for b in bias]
        for pixel in thumb.getdata():
            pixel = pixel[:3]  # Ignore alpha channel
            mu = sum(pixel) / 3
            SSE += sum(
                (pixel[i] - mu - bias[i]) * (pixel[i] - mu - bias[i]) for i in [0, 1, 2]
            )
        MSE = float(SSE) / (thumb_size * thumb_size)
        if MSE <= MSE_cutoff:
            return True
        else:
            return False
    elif len(bands) == 1:
        return True
    else:
        return False  # Assume colored by default


def make_thumbnail(a, ttype, instrument_type):

    if f"cutout{instrument_type}" not in a:
        return None

    cutout_data = a[f"cutout{instrument_type}"]["stampData"]
    with gzip.open(io.BytesIO(cutout_data), "rb") as f:
        with fits.open(io.BytesIO(f.read()), ignore_missing_simple=True) as hdu:
            # header = hdu[0].header
            data_flipped_y = np.flipud(hdu[0].data)
    plt.close("all")
    fig = plt.figure()
    fig.set_size_inches(4, 4, forward=False)
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    fig.add_axes(ax)

    # replace nans with median:
    img = np.array(data_flipped_y)
    # replace dubiously large values
    xl = np.greater(np.abs(img), 1e20, where=~np.isnan(img))
    if img[xl].any():
        img[xl] = np.nan
    if np.isnan(img).any():
        median = float(np.nanmean(img.flatten()))
        img = np.nan_to_num(img, nan=median)

    norm = ImageNormalize(
        img,
        stretch=LinearStretch() if instrument_type == "Difference" else LogStretch(),
    )
    img_norm = norm(img)
    normalizer = AsymmetricPercentileInterval(lower_percentile=1, upper_percentile=100)
    vmin, vmax = normalizer.get_limits(img_norm)
    ax.imshow(img_norm, cmap="bone", origin="lower", vmin=vmin, vmax=vmax)
    buff = io.BytesIO()
    plt.savefig(buff, format="png", dpi=42)
    plt.close(fig)
    buff.seek(0)

    thumb = {
        "obj_id": a["objectId"],
        "data": base64.b64encode(buff.read()).decode("utf-8"),
        "ttype": ttype,
    }

    return thumb
