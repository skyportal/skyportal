from astropy.io import fits
from astropy.visualization.stretch import SinhStretch
from astropy.visualization import ImageNormalize, ZScaleInterval
import io
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pysedm
import tempfile

np.seterr(all="ignore")  # ignore numpy warnings from astropy normalization


def get_fits_preview(
    image_name,
    image_data,
    figsize=(8, 8),
    output_format='png',
):
    """
    Return an image of fits data

    Parameters
    ----------
    image_data : bytes
        Bytes representation of the fits images
    figsize : tuple, optional
        Matplotlib figsize of the png created
    output_format : str, optional
        "pdf" or "png" -- determines the format of the returned plot
    Returns
    -------
    data
        Byte representation of the data for display

    """

    # first, get the file_type (fits or fits.fz)
    file_type = image_name.split(".")[-1]
    if file_type == "fz":
        file_type = ".fits.fz"
    else:
        file_type = ".fits"

    matplotlib.use("Agg")
    fig = plt.figure(figsize=figsize, constrained_layout=False)

    try:
        with tempfile.NamedTemporaryFile(suffix=file_type, mode="wb", delete=True) as f:
            f.write(image_data)
            f.flush()
            cube = pysedm.sedm.load_sedmcube(f.name)

            with tempfile.NamedTemporaryFile(
                suffix=f".{output_format}", mode="wb", delete=True
            ) as h:
                cube.show(savefile=h.name)
                h.flush()
                with open(h.name, mode='rb') as g:
                    data = g.read()
            return data
    except Exception:
        with tempfile.NamedTemporaryFile(suffix=file_type, mode="wb", delete=True) as f:
            f.write(image_data)
            f.flush()
            hdul = fits.open(f.name)
            hdul_index = -1
            for i, hdu in enumerate(hdul):
                if hdu.data is not None:
                    hdul_index = i
                    break
            if hdul_index == -1:
                raise IndexError("No image data found in fits file")
            image = hdul[hdul_index].data.astype(np.float32)

            norm = ImageNormalize(
                image, interval=ZScaleInterval(), stretch=SinhStretch()
            )
            plt.imshow(image, cmap='gray', norm=norm, origin='lower')
            plt.colorbar(fraction=0.046, pad=0.04)

            buf = io.BytesIO()
            fig.savefig(buf, format=output_format)
            plt.close(fig)
            buf.seek(0)
            return buf.read()
