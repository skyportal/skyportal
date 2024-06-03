from PIL import Image, ImageStat, UnidentifiedImageError

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()

# Default classification parameters
thumb_size = cfg["image_grayscale_params.thumb_size"]
MSE_cutoff = cfg["image_grayscale_params.MSE_cutoff"]
adjust_color_bias = cfg["image_grayscale_params.adjust_color_bias"]

log = make_log('thumbnail')


def get_thumbnail_alt_link(name, ra, dec):
    alt = {
        "new": "discovery image",
        "ref": "pre-discovery (reference) image",
        "sub": "subtracted image",
        "sdss": "Link to SDSS Navigate tool",
        "ls": "Link to Legacy Survey DR9 Image Access",
        "ps1": "Link to PanSTARRS-1 Image Access",
    }
    link = {
        "sdss": f"https://skyserver.sdss.org/dr16/en/tools/chart/navi.aspx?opt=G&ra={ra}&dec={dec}&scale=0.25",
        "ls": f"https://www.legacysurvey.org/viewer?ra={ra}&dec={dec}&layer=ls-dr9&photoz-dr9&zoom=16&mark={ra},{dec}",
        "ps1": f"https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos={ra}+{dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=",
    }
    return alt.get(name, ""), link.get(name, "")


def get_thumbnail_header(thumb_type):
    header = {
        "ls": "LEGACY SURVEY DR9",
        "ps1": "PANSTARRS DR2",
    }
    return header.get(thumb_type, thumb_type.upper())


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
