FROM 32bit/debian:jessie
RUN DEBIAN_FRONTEND=noninteractive apt-get update  --fix-missing && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python-pip \
        python-dev \
        git \
        libssl-dev \
        libffi-dev

RUN pip install --upgrade pip setuptools
RUN pip install --upgrade {buildmaster_packages}

RUN groupadd -r {user} -g {gid} && useradd -r -g {user} -u {uid} {user}
RUN mkdir -p /buildmaster
RUN chown {user}:{user} -R /buildmaster

VOLUME /buildmaster

USER {user}
WORKDIR /buildmaster
