FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV NODE_MAJOR=20
ENV NPM_CONFIG_LEGACY_PEER_DEPS=true
ENV PATH="/root/.cargo/bin:${PATH}"
ENV SNCOSMO_DATA_DIR=/skyportal/persistentdata/sncosmo

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common ca-certificates gnupg \
    python3 python3-venv python3-dev libpq-dev supervisor libgdal-dev \
    git postgresql-client vim nano screen htop \
    libcurl4-gnutls-dev libgnutls28-dev && \
    nginx libnginx-mod-http-brotli-static libnginx-mod-http-brotli-filter cargo && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    curl -fsSL https://bun.sh/install | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    useradd --create-home --shell /bin/bash skyportal && \
    uv venv /skyportal_env --python 3.11

ADD . /skyportal
WORKDIR /skyportal

RUN bash -c "\
    cp docker.yaml config.yaml && \
    python3 -m venv /skyportal_env && \
    source /skyportal_env/bin/activate && \
    uv pip install --upgrade pip wheel packaging setuptools --no-cache && \
    uv pip install -r baselayer/requirements.txt --no-cache && \
    uv pip install -r requirements.txt --no-cache && \
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
    chown -R skyportal.skyportal /skyportal/persistentdata/sncosmo && \
    # we remove the cache and temp files to reduce the image size
    rm -rf /root/.cache/pip && rm -rf /tmp/* && \
    # we remove some unused data from the gwemopt package to reduce the image size
    rm -rf /skyportal_env/lib/python3.11/site-packages/gwemopt/data/tesselations/*.tess"


USER skyportal

# edit the exposed port to match the one in the
# docker.yaml, or just ignore it if you are
# specifying ports in docker-compose.yaml already
EXPOSE 5000

CMD bash -c "source /skyportal_env/bin/activate && \
    (make log &) && \
    make run_production"
