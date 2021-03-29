from PIL import Image, ImageStat, UnidentifiedImageError


def image_is_grayscale(file, thumb_size=40, MSE_cutoff=22, adjust_color_bias=True):
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
