FROM 32bit/debian:jessie
RUN apt-get update --fix-missing
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
           python-dev \
           python-pip \
           git \
           zip

RUN pip install {buildslave_packages}

RUN groupadd -r {user} -g {gid} && useradd -r -g {user} -u {uid} {user}
RUN mkdir -p /buildslave
RUN chown {user}:{user} -R /buildslave


# Adapt this if you need sudo
#RUN yum install -y sudo
#RUN groupadd -r sudo
#RUN echo "{user}:{user}" | chpasswd && usermod -a -G sudo {user}
#RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
#RUN echo 'Defaults:%sudo !requiretty' >> /etc/sudoers

USER {user}
WORKDIR /buildslave

ENTRYPOINT \
    rm -f twistd.pid \
    rm -f buildbot.tac \
    && buildslave create-slave . "$MASTER_PORT_9989_TCP_ADDR:$MASTER_PORT_9989_TCP_PORT" {slave_name} {slave_password} \
    && buildslave start --nodaemon

