#!/bin/bash

set -ex

section "install.base.requirements"

# Install v1.7 or newer of nginx to support 'if' statement for logging
sudo apt-add-repository -y ppa:nginx/stable
sudo apt update
sudo apt install -y nginx firefox graphviz-dev graphviz

nginx -v
firefox --version

pip install --upgrade pip
hash -d pip  # find upgraded pip
section_end "install.base.requirements"

section "install.baselayer.requirements"
npm -g install npm@next
npm --version
node --version

# TODO replace w/ baselayer dependent build info
if [[ -n ${TRIGGERED_FROM_REPO} ]]; then
    mkdir cesium-clone
    cd cesium-clone
    git init
    git remote add origin git://github.com/${TRIGGERED_FROM_REPO}
    git fetch --depth=1 origin ${TRIGGERED_FROM_BRANCH}
    git checkout -b ${TRIGGERED_FROM_BRANCH} ${TRIGGERED_FROM_SHA}
    pip install .
    cd ..
fi

pip list --format=columns
section_end "install.baselayer.requirements"


section "init.db"
make db_init
section_end "init.db"


section "run.make.dependencies"
make dependencies
pip install -r requirements.docs.txt
pip list --format=columns
set +ex
npm ls --depth 0
set -ex
nginx -v
section_end "run.make.dependencies"


section "install.geckodriver.and.selenium"

GECKO_VER=0.27.0
CACHED_DOWNLOAD_DIR=~/.local/downloads

wget https://github.com/mozilla/geckodriver/releases/download/v${GECKO_VER}/geckodriver-v${GECKO_VER}-linux64.tar.gz --directory-prefix=${CACHED_DOWNLOAD_DIR} --no-clobber
sudo tar -xzf ${CACHED_DOWNLOAD_DIR}/geckodriver-v${GECKO_VER}-linux64.tar.gz -C /usr/local/bin
which geckodriver
geckodriver --version
pip install --upgrade selenium
python -c "import selenium; print(f'Selenium {selenium.__version__}')"
section_end "install.geckodriver.and.selenium"
