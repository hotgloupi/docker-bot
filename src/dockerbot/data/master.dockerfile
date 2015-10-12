FROM 32bit/debian:jessie
RUN apt-get update --fix-missing
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
                    python-pip \
                    python-dev \
                    git
RUN pip install \
        docker-py \
        requests \
        https://pypi.python.org/packages/source/b/buildbot/buildbot-0.8.12.tar.gz#md5=c61fa219942f8a1ed43cdbc1e4ef0187

RUN groupadd -r {user} -g {gid} && useradd -r -g {user} -u {uid} {user}
RUN mkdir -p /buildmaster
RUN chown {user}:{user} -R /buildmaster

VOLUME /buildmaster

USER {user}
WORKDIR /buildmaster
