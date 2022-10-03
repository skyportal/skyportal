from astropy.io import fits
import copy
import io
import matplotlib
import matplotlib.pyplot as plt
import pysedm
import tempfile


def get_fits_preview(
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

    matplotlib.use("Agg")
    fig = plt.figure(figsize=figsize, constrained_layout=False)

    image_data_copy = copy.deepcopy(image_data)
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.' + output_format) as f:
            cube = pysedm.sedm.load_sedmcube(image_data)
            cube.show(savefile=f.name)
            f.flush()
            with open(f.name, mode='rb') as g:
                data = g.read()
            return data

    except Exception:
        image_data = fits.getdata(image_data_copy, ext=0, ignore_missing_simple=True)
        plt.imshow(image_data, cmap='gray')

        buf = io.BytesIO()
        fig.savefig(buf, format=output_format)
        plt.close(fig)
        buf.seek(0)

        return buf.read()
