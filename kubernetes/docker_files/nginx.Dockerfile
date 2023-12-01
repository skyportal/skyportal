FROM --platform=linux/amd64 ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y python3 python3-venv python3-dev \
    libpq-dev supervisor \
    git vim nano screen htop cargo

RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get update && \
    apt-get install -y nodejs nginx

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

ADD baselayer /skyportal/baselayer
ADD package.json /skyportal/package.json
ADD webpack.config.js /skyportal/webpack.config.js
ADD README.md /skyportal/README.md
ADD config.yaml.defaults /skyportal/config.yaml.defaults
ADD kubernetes/kubernetes.yaml /skyportal/docker.yaml
ADD Makefile /skyportal/Makefile
ADD static /skyportal/static
ADD skyportal/__init__.py /skyportal/skyportal/__init__.py

WORKDIR /skyportal

# this env variable can be overwritten in a k8 config to start specific services
# it can be a comma seperated list
ENV SERVICES_ENABLED "nginx"

RUN bash -c "\
    cp baselayer/services/nginx/k8.nginx.conf.template baselayer/services/nginx/nginx.conf.template && \
    cp docker.yaml config.yaml && \
    \
    source /skyportal_env/bin/activate && \
    export NPM_CONFIG_LEGACY_PEER_DEPS=true && \
    make dependencies_js"

RUN bash -c "\
    source /skyportal_env/bin/activate && \
    make system_setup_baselayer && \
    \
    ./node_modules/.bin/webpack --mode=production && \
    rm -rf node_modules && \
    \
    chown -R skyportal.skyportal /skyportal_env && \
    chown -R skyportal.skyportal /skyportal && \
    \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*"

USER skyportal
EXPOSE 8000

CMD bash -c "source /skyportal_env/bin/activate && \
    rm baselayer/conf/supervisor/supervisor.conf && \
    make fill_conf_values && \
    make service_setup && \
    (make log &) && \
    make run_production"
