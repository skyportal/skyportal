FROM ubuntu:18.04

RUN apt-get update && \
    apt-get install -y curl build-essential software-properties-common && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y python3 python3-venv python3-dev \
                       libpq-dev supervisor \
                       git nginx nodejs postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    useradd --create-home --shell /bin/bash skyportal

RUN python3.6 -m venv /skyportal_env && \
    \
    bash -c "source /skyportal_env/bin/activate && \
    pip install --upgrade pip"

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ADD . /skyportal
WORKDIR /skyportal

RUN bash -c "\
    source /skyportal_env/bin/activate && \
    \
    make -C baselayer paths && \
    (make -f baselayer/Makefile baselayer dependencies || make -C baselayer dependencies)"

RUN bash -c "\
    \
    (make -f baselayer/Makefile bundle || make -c baselayer bundle) && \
    rm -rf node_modules && \
    \
    chown -R skyportal.skyportal /skyportal_env && \
    chown -R skyportal.skyportal /skyportal && \
    \
    cp docker.yaml config.yaml"

USER skyportal

EXPOSE 5000

CMD bash -c "source /skyportal_env/bin/activate && \
             (make log &) && \
             make run_production"
