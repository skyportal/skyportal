# Image Analysis

This feature allows users to upload FITS images from observations of a source, and then use STDPipe to **extract the photometry from the image**.
As this feature requires additional system dependencies, we choose to make it optional.

## Installing System Dependencies required by STDpipe

### Debian-based Linux and WSL

```
sudo apt install sextractor scamp psfex swarp
```

Also, one needs to install `snid`. To install it, you can run the following commands which will git clone and run an install script (works only on ubuntu for now, both arm64 and amd64)

```
git clone https://github.com/Theodlz/snid-install-ubuntu.git && \
cd snid-install-ubuntu && sudo chmod +x install.sh && sudo bash ./install.sh
```

### Mac OSX

We can use Homebrew to install dependencies (Macports should also be possible in a similar fashion). We have written a short bash script that can be modified to build the dependencies:

```
#!/bin/bash

INSTALL_DIR="FULL_DIRECTORY_PATH_HERE";
mkdir $INSTALL_DIR;

brew install sextractor
brew install openblas
brew install cfitsio
brew install fftw

cd $INSTALL_DIR;
git clone git@github.com:astromatic/scamp.git
cd scamp;
sh autogen.sh
mkdir $INSTALL_DIR/scamp-build
./configure --prefix=$INSTALL_DIR/scamp-build \
  --with-fftw-libdir=/opt/homebrew/Cellar/fftw/3.3.10_1/lib \
  --with-fftw-incdir=/opt/homebrew/Cellar/fftw/3.3.10_1/include \
  --enable-openblas \
  --with-openblas-libdir=/opt/homebrew/opt/openblas/lib \
  --with-openblas-incdir=/opt/homebrew/opt/openblas/include \
make;
make install;

cd $INSTALL_DIR;
git clone git@github.com:astromatic/swarp.git
cd swarp;
sh autogen.sh
mkdir $INSTALL_DIR/swarp-build
./configure --prefix=$INSTALL_DIR/swarp-build \
    --with-cfitsio-incdir=/opt/homebrew/Cellar/cfitsio/4.2.0/include \
    --with-cfitsio-libdir=/opt/homebrew/Cellar/cfitsio/4.2.0/lib
make;
make install;

cd $INSTALL_DIR;
git clone git@github.com:astromatic/psfex.git
cd psfex;
sh autogen.sh
mkdir $INSTALL_DIR/psfex-build
./configure --prefix=/Users/mcoughlin/Code/ZTF/psfex-build \
    --with-fftw-libdir=/opt/homebrew/Cellar/fftw/3.3.10_1/lib \
    --with-fftw-incdir=/opt/homebrew/Cellar/fftw/3.3.10_1/include \
    --enable-openblas --with-openblas-libdir=/opt/homebrew/opt/openblas/lib \
    --with-openblas-incdir=/opt/homebrew/opt/openblas/include
make;
make install;
```

psfex can be installed
./configure --prefix=/Users/mcoughlin/Code/ZTF/psfex-build --with-fftw-libdir=/opt/homebrew/Cellar/fftw/3.3.10_1/lib --with-fftw-incdir=/opt/homebrew/Cellar/fftw/3.3.10_1/include --enable-openblas --with-openblas-libdir=/opt/homebrew/opt/openblas/lib --with-openblas-incdir=/opt/homebrew/opt/openblas/include

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
To increase the maximum request size, change the `max_body_size: 10` parameter in the `config.yaml` file to a larger value, like `100` (in MB).

Also, as mentioned earlier, you need to add `image_analysis: ` in the `config.yaml` file. By default, it is not present.
Later, this field of the config file will be used to configure the image analysis feature.

Moreover, in the app.routes, uncomment the following lines:
```
- path: "/source/:id/image_analysis"
  component: ImageAnalysisPage
```
This will add the frontend route to the image analysis page.

**If you are deploying SkyPortal using Docker, don't forget to add the same changes to the `docker.yaml` file as well.**

## Deploy using Docker

If you are deploying SkyPortal using Docker, you need to uncomment a few lines from the Dockerfile, which are commented out by default. These lines are here to install the system and python dependencies required by STDpipe.

```
RUN apt-get update && \
    apt-get install -y sextractor scamp psfex
```

and

```
RUN git clone https://github.com/Theodlz/snid-install-ubuntu.git && \
    cd snid-install-ubuntu && chmod +x install.sh && bash ./install.sh

RUN python3 -m venv /skyportal_env && \
    bash -c "source /skyportal_env/bin/activate && \
    git clone https://github.com/karpov-sv/stdpipe.git && \
    cd stdpipe && pip install -e . && \
    pip install astroscrappy"
```

Again, add the same lines mentioned in the Configuration section to the `docker.yaml` file.

## Usage

Go to the page of a source, and click on the `Image Analysis` right button under the photometry plot. It will redirect you to the image analysis page.
Then, fill in the fields required by the form, and upload the image. The operations performed by STDpipe are computation intensive, so it can take several minutes to extract the photometry from the image.

**The image must be a compressed FITS file (.fits.fz). We recommend compressing it with funpack.**

Now, click submit. When the photometry is extracted (it will take around a minute), you should receive a frontend notification.
To see if STDpipe managed to extract the photometry from your image, you can simply go back to the source page and see if the photometry is there on the plot, or in the `manage data` table.
