FROM 32bit/debian:jessie
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
           python-dev \
           python-pip \
           git \
           zip
RUN pip install buildbot-slave
RUN groupadd -r buildbot && useradd -r -g buildbot buildbot
RUN mkdir /buildslave && chown buildbot:buildbot /buildslave
# Install your build-dependencies here ...
USER buildbot
WORKDIR /buildslave
ENTRYPOINT \
    buildslave create-slave . "$MASTER_PORT_9989_TCP_ADDR:$MASTER_PORT_9989_TCP_PORT" {slave_name} {slave_password} \
    && buildslave start --nodaemon
