from astropy.io import fits
from astropy.visualization.stretch import SinhStretch
from astropy.visualization import ImageNormalize, ZScaleInterval
from astropy.table import Table
import healpy
import io
import ligo.skymap.bayestar as ligo_bayestar
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pysedm
import tempfile

np.seterr(all="ignore")  # ignore numpy warnings from astropy normalization

SKYMAP_ORDER = healpy.nside2order(512)


def get_fits_preview(
    image_name,
    image_data,
    figsize=None,
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

    # try reading the data as a sedm cube
    try:
        fig = plt.figure(
            figsize=(8, 8) if not figsize else figsize, constrained_layout=False
        )
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
        pass

    # try reading the data as a fits image
    try:
        fig = plt.figure(
            figsize=(8, 8) if not figsize else figsize, constrained_layout=False
        )
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
    except Exception:
        pass

    # try reading the data as a fits localization skymap
    try:
        fig = plt.figure(
            figsize=(14, 8) if not figsize else figsize, constrained_layout=False
        )
        with tempfile.NamedTemporaryFile(suffix=file_type, mode="wb", delete=True) as f:
            f.write(image_data)
            f.flush()
            hdul = fits.open(f.name)
            # read the content of the skymap
            skymap = hdul[1].data

            # the skymap should contain at least 2 columns: UNIQ and PROBDENSITY
            if not set(list(skymap.columns.names)).issuperset({'UNIQ', 'PROBDENSITY'}):
                raise ValueError("Invalid skymap format")

            table_2d = Table(
                [
                    np.asarray(skymap['UNIQ'], dtype=np.int64),
                    np.asarray(skymap['PROBDENSITY'], dtype=np.float64),
                ],
                names=['UNIQ', 'PROBDENSITY'],
            )

            prob = ligo_bayestar.rasterize(table_2d, SKYMAP_ORDER)['PROB']
            prob = healpy.reorder(prob, 'NESTED', 'RING')

            ax = plt.axes([0.05, 0.05, 0.9, 0.9], projection='astro hours mollweide')

            ax.grid()
            ax.imshow_hpx(prob, cmap='cylon')

            buf = io.BytesIO()
            fig.savefig(buf, format=output_format)
            plt.close(fig)
            buf.seek(0)
            return buf.read()
    except Exception:
        pass

    raise ValueError("Could not read image data")
