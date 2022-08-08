# Image Analysis using STDPipe

This feature allows user to upload FITS images from observations a source, and then use STDPipe **extract the photometry from the image**.
As this feature requires the installation of additional system dependencies, we choose to make it optional.
By default, this feature is deactivated in the `config.yaml.default`. To activate it, set `image_analysis` to `True` in the `config.yaml`.

## Installing System Dependencies required by STDpipe (Debian-based Linux and WSL)

```
sudo apt install sextractor scamp psfex swarp
```

## Installing STDpipe

As of right now, STDpipe is in development, and not available on pypi or conda yet.
STDpipe is available at https://github.com/karpov-sv/stdpipe and is mirrored at https://gitlab.in2p3.fr/icare/stdpipe

1. Get the installer

```
cd skyportal
git clone https://github.com/karpov-sv/stdpipe.git
```


2. Installing it in your virtual environment

```
source skyportal_env/bin/activate
cd stdpipe
python3 setup.py develop --user
```

## Usage

Go to the page of a source, and add `/image_analysis` at the end of the URL. It should look something like `http://localhost:5000/source/ZTF22aayaehk/image_analysis`.
Then, fill in the fields required by the form, and upload the image.

**The image must be a compressed FITS file (.fits.fz). We recommend compressing it with funpack.**

Now, click submit. When the photometry is extracted (it will take around a minute), you should receive a frontend notification.
To see if STDpipe managed to extract the photometry from your image, you can simply go back to the source page and see if the photometry is there on the plot, or in the `manage data` table.
