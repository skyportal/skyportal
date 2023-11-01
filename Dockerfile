FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# lines to comment if you do not want to use the image analysis feature
RUN apt-get update && \
    apt-get install -y sextractor scamp psfex

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    NODE_MAJOR=20 && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y python3 python3-venv python3-dev \
    libpq-dev supervisor \
    git nginx nodejs postgresql-client vim nano screen htop \
    libcurl4-gnutls-dev libgnutls28-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    useradd --create-home --shell /bin/bash skyportal

RUN python3 -m venv /skyportal_env && \
    \
    bash -c "source /skyportal_env/bin/activate && \
    pip install --upgrade pip==22.2.2 wheel numpy"


# lines to uncomment if you do not want to use the image analysis feature
RUN git clone https://github.com/Theodlz/snid-install-ubuntu.git && \
    cd snid-install-ubuntu && chmod +x install.sh && bash ./install.sh

# lines to uncomment if you do not want to use the image analysis feature
RUN python3 -m venv /skyportal_env && \
    bash -c "source /skyportal_env/bin/activate && \
    git clone https://github.com/karpov-sv/stdpipe.git && \
    cd stdpipe && pip install -e . && \
    pip install astroscrappy"

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ADD . /skyportal
WORKDIR /skyportal

RUN bash -c "\
    cp docker.yaml config.yaml && \
    \
    source /skyportal_env/bin/activate && \
    export NPM_CONFIG_LEGACY_PEER_DEPS=true && \
    make system_setup && \
    \
    ./node_modules/.bin/webpack --mode=production && \
    rm -rf node_modules && \
    \
    chown -R skyportal.skyportal /skyportal_env && \
    chown -R skyportal.skyportal /skyportal && \
    \
    mkdir -p /skyportal/static/thumbnails && \
    chown -R skyportal.skyportal /skyportal/static/thumbnails && \
    \
    mkdir -p /skyportal/persistentdata/analysis && \
    chown -R skyportal.skyportal /skyportal/persistentdata/analysis && \
    \
    mkdir -p /skyportal/persistentdata/dustmap && \
    chown -R skyportal.skyportal /skyportal/persistentdata/dustmap && \
    \
    mkdir -p /skyportal/persistentdata/phot_series && \
    chown -R skyportal.skyportal /skyportal/persistentdata/phot_series && \
    \
    mkdir -p /skyportal/persistentdata/sncosmo && \
    chown -R skyportal.skyportal /skyportal/persistentdata/sncosmo"

ENV SNCOSMO_DATA_DIR=/skyportal/persistentdata/sncosmo

USER skyportal

EXPOSE 5000

CMD bash -c "source /skyportal_env/bin/activate && \
    (make log &) && \
    make run_production"
