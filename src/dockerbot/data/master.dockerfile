FROM 32bit/debian:jessie

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y python-pip python-dev supervisor
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y git
RUN pip install docker-py requests
RUN pip install https://pypi.python.org/packages/source/b/buildbot/buildbot-0.8.12.tar.gz#md5=c61fa219942f8a1ed43cdbc1e4ef0187
#RUN pip install https://pypi.python.org/packages/2.7/b/buildbot/buildbot-0.9.0b2-py2-none-any.whl#md5=bb41d083cc05c75d3a4a5da436400d86
#RUN git clone -q https://github.com/buildbot/buildbot.git --depth 1 -b  /tmp/buildbot-sources
#RUN cd /tmp/buildbot-sources/master && python setup.py install
ADD buildbot.conf /etc/supervisor/conf.d/buildbot.conf
EXPOSE 8020
EXPOSE 9989

CMD ["/usr/bin/supervisord", "-n"]
