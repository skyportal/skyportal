FROM --platform=linux/amd64 ubuntu:22.04 as core

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y python3 python3-venv python3-dev \
    libpq-dev supervisor \
    libcurl4-openssl-dev libssl-dev \
    git vim nano screen htop cargo

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    useradd --create-home --shell /bin/bash skyportal

ENV PATH="/root/.cargo/bin:${PATH}"

RUN python3 -m venv /skyportal_env && \
    \
    bash -c "source /skyportal_env/bin/activate && \
    pip install --upgrade pip==22.2.2 wheel numpy"

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

FROM core as baselayer

ADD baselayer /skyportal/baselayer
ADD README.md /skyportal/README.md
ADD config.yaml.defaults /skyportal/config.defaults.yaml
ADD kubernetes/kubernetes.yaml /skyportal/config.yaml
ADD Makefile /skyportal/Makefile
ADD alembic.ini /skyportal/alembic.ini
ADD alembic /skyportal/alembic
WORKDIR /skyportal

RUN bash -c "\
    source /skyportal_env/bin/activate && \
    make system_setup_baselayer && \
    \
    chown -R skyportal.skyportal /skyportal_env && \
    chown -R skyportal.skyportal /skyportal && \
    \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*"

USER skyportal

CMD bash -c "source /skyportal_env/bin/activate && \
    rm baselayer/conf/supervisor/supervisor.conf && \
    make fill_conf_values && \
    make service_setup && \
    (make log &) && \
    make run_baselayer_service"

FROM core as skyportal

ADD . /skyportal
ADD kubernetes/kubernetes.yaml /skyportal/config.yaml
WORKDIR /skyportal

RUN bash -c "\
    source /skyportal_env/bin/activate && \
    export SERVICES_ENABLED=app && \
    make system_setup_python_only && \
    \
    chown -R skyportal.skyportal /skyportal_env && \
    chown -R skyportal.skyportal /skyportal && \
    \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*"

USER skyportal

# this env variable can be overwritten in a k8 config to start specific services
# it can be a comma seperated list
ENV SERVICES_ENABLED "app"

CMD bash -c "source /skyportal_env/bin/activate && \
    export SERVICES_ENABLED=app && \
    rm baselayer/conf/supervisor/supervisor.conf && \
    make fill_conf_values && \
    make service_setup && \
    (make log &) && \
    make run_production"
