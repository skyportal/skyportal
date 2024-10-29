FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y python3 python3-venv python3-dev \
    libpq-dev supervisor \
    git postgresql-client vim nano screen htop \
    libcurl4-gnutls-dev libgnutls28-dev && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    curl -fsSL https://bun.sh/install | bash && \
    apt-get install -y cargo

ENV PATH="/root/.cargo/bin:${PATH}"

# we install nginx with brotli support from ppa:ondrej/nginx-mainline
RUN add-apt-repository ppa:ondrej/nginx-mainline -y && \
	apt update -y && \
	apt install -y nginx libnginx-mod-http-brotli-static libnginx-mod-http-brotli-filter

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    useradd --create-home --shell /bin/bash skyportal

RUN uv venv /skyportal_env --python 3.11 && \
    bash -c "source /skyportal_env/bin/activate && \
    pip install --upgrade pip==22.2.2 wheel numpy"

# install snid
RUN git clone https://github.com/Theodlz/snid-install-ubuntu.git && \
    cd snid-install-ubuntu && chmod +x install.sh && bash ./install.sh

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ADD . /skyportal
WORKDIR /skyportal

RUN bash -c "\
    cp docker.yaml config.yaml && \
    \
    source /skyportal_env/bin/activate && \
    make system_setup && \
    \
    ./node_modules/.bin/rspack --mode=production && \
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
