# Image Analysis

This feature allows user to upload FITS images from observations a source, and then use STDPipe to **extract the photometry from the image**.
As this feature requires additional system dependencies, we choose to make it optional.

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
pip install -e .
```

## Configuration file

By default, the app allows a maximum request size of 10MB (from the client). This is not enough for someone to upload most .fits files (compressed or not).
To increase the maximum request size, change the `max_body_size: 10` parameter in the `config.yaml` file to a larger value, like a `100` (in MB).

Also, as mentionned earlier, you need to set `image_analysis` to `True` in the `config.yaml` file. By default, it is set to `False`.

**If you are deploying SkyPortal using Docker, don't forget to add the same changes to the `docker.yaml` file as well.**

## Deploy using Docker

If you are deploying SkyPortal using Docker, you need to uncomment a few lines from the Dockerfile, which are commented out by default. These lines are here to install the system and python dependencies required by STDpipe.

```
# RUN apt-get update && \
#     apt-get install -y sextractor scamp psfex
```

and

```
# RUN python3 -m venv /skyportal_env && \
#     \
#     bash -c "source /skyportal_env/bin/activate && \
#     git clone https://github.com/karpov-sv/stdpipe.git && \
#     cd stdpipe && pip install -e . && \
#     pip install astroscrappy"
```

Again, add the same lines mentionned in the previous section to the `docker.yaml` file.

## Usage

Go to the page of a source, and add `/image_analysis` at the end of the URL. It should look something like `http://localhost:5000/source/ZTF22aayaehk/image_analysis`.
Then, fill in the fields required by the form, and upload the image.
Otherwise, you can find a button labelled `Image Analysis` right under the photometry plot. It will redirect you to the image analysis page.

**The image must be a compressed FITS file (.fits.fz). We recommend compressing it with funpack.**

Now, click submit. When the photometry is extracted (it will take around a minute), you should receive a frontend notification.
To see if STDpipe managed to extract the photometry from your image, you can simply go back to the source page and see if the photometry is there on the plot, or in the `manage data` table.
