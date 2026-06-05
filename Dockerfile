FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV NODE_MAJOR=20
ENV NPM_CONFIG_LEGACY_PEER_DEPS=true
ENV PATH="/root/.cargo/bin:${PATH}"
# Point sncosmo at the vendored data in the skyportal-data submodule (baked in
# by `ADD . /skyportal`). SNCOSMO_DATA_DIR takes precedence over the config's
# misc.sncosmo_data_folder, so set it to the same location. The chown of
# /skyportal below keeps it writable for any runtime fallback fetch.
ENV SNCOSMO_DATA_DIR=/skyportal/skyportal-data/sncosmo
ENV UV_NO_DEV=1
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common ca-certificates gnupg \
    python3 python3-venv python3-dev libpq-dev supervisor libgdal-dev \
    git postgresql-client vim nano screen htop rsync procps \
    libcurl4-gnutls-dev libgnutls28-dev libkrb5-dev && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    apt-get update && \
    apt-get install -y cargo nodejs nginx libnginx-mod-http-brotli-static libnginx-mod-http-brotli-filter unzip && \
    # bun is the project's package manager (per packageManager in package.json);
    # baselayer's check_js_deps.sh auto-detects it from there.
    curl -fsSL https://bun.sh/install | bash && \
    install -m 0755 /root/.bun/bin/bun /usr/local/bin/bun && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.bun

ARG SKYPORTAL_UID=1000
ARG SKYPORTAL_GID=1000
RUN groupadd -g $SKYPORTAL_GID skyportal && \
    useradd -u $SKYPORTAL_UID -g $SKYPORTAL_GID --create-home --shell /bin/bash skyportal

ADD . /skyportal
WORKDIR /skyportal

RUN bash -c "\
    cp docker.yaml config.yaml && \
    uv venv && \
    source .venv/bin/activate && \
    uv sync --inexact && \
    make system_setup && \
    \
    ./node_modules/.bin/rspack --mode=production && \
    rm -rf node_modules && \
    \
    chown -R skyportal.skyportal .venv && \
    chown -R skyportal.skyportal /skyportal && \
    chown -R skyportal.skyportal /opt/uv-python && \
    \
    mkdir -p /skyportal/static/thumbnails && \
    chown -R skyportal.skyportal /skyportal/static/thumbnails && \
    \
    mkdir -p /skyportal/persistentdata/analysis && \
    chown -R skyportal.skyportal /skyportal/persistentdata/analysis && \
    \
    mkdir -p /skyportal/persistentdata/comments && \
    chown -R skyportal.skyportal /skyportal/persistentdata/comments && \
    \
    mkdir -p /skyportal/persistentdata/dustmap && \
    chown -R skyportal.skyportal /skyportal/persistentdata/dustmap && \
    \
    mkdir -p /skyportal/persistentdata/phot_series && \
    chown -R skyportal.skyportal /skyportal/persistentdata/phot_series && \
    \
    # sncosmo data (bandpasses, models) is vendored in the skyportal-data
    # submodule and baked into the image by `ADD . /skyportal`, with
    # SNCOSMO_DATA_DIR pointing at it — so there is no network warm-up at
    # build time. The chown of /skyportal above keeps it writable for any
    # runtime fallback fetch of a bandpass not present in the vendored set.
    \
    # we remove the cache and temp files to reduce the image size
    rm -rf /root/.cache/pip && rm -rf /root/.cache/uv && rm -rf /tmp/* && \
    # we remove some unused data from the gwemopt package to reduce the image size
    rm -rf .venv/lib/python3.12/site-packages/gwemopt/data/tesselations/*.tess"


USER skyportal

# edit the exposed port to match the one in the
# docker.yaml, or just ignore it if you are
# specifying ports in docker-compose.yaml already
EXPOSE 5000

CMD ["bash", "-c", "source .venv/bin/activate && (make log &) && make run_production"]
