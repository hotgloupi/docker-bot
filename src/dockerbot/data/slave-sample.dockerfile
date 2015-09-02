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
RUN buildslave create-slave . {master_hostname} {slave_name} {slave_password}
ENTRYPOINT ["/usr/local/bin/buildslave"]
CMD ["start", "--nodaemon"]
