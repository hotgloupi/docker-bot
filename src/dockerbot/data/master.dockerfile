FROM 32bit/debian:jessie
RUN apt-get update --fix-missing
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
                    python-pip \
                    python-dev \
                    git
RUN pip install {buildmaster_packages}

RUN groupadd -r {user} -g {gid} && useradd -r -g {user} -u {uid} {user}
RUN mkdir -p /buildmaster
RUN chown {user}:{user} -R /buildmaster

VOLUME /buildmaster

USER {user}
WORKDIR /buildmaster
