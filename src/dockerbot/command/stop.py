from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess

from ..error import Error
from ..log import warn, status, debug_stream
from .. import docker
from .. import config

def main(force, build_directory, timeout = 6):
    if build_directory is None:
        build_directory = os.getcwd()
    build_directory = os.path.abspath(build_directory)
    marker = os.path.join(build_directory, '.dockerbot-build')
    if not os.path.exists(marker):
        raise Error("%s is not a valid dockerbot build directory" % build_directory)
    with open(marker) as f:
        project_directory = f.read().strip()

    client = docker.Client()
    master_container_path = os.path.abspath(os.path.join(build_directory, 'master.container'))
    if os.path.exists(master_container_path):
        with open(master_container_path) as f:
            container_id = f.read().strip()
        if container_id in client.containers:
            if client.is_container_alive(container_id):
                status('Stopping the master container')
                client.cmd('stop', '-t', str(timeout), container_id)
            status('Removing the master container')
            state = client.cmd('rm', '-f', container_id)
        else:
            warn('Cannot find', container_id)
        os.unlink(master_container_path)

    cfg = config.load(build_directory,
                      os.path.join(project_directory, 'dockerbot.yml'))

    slave_images = set(
        slave['image-name'] for slave in cfg['slaves'].values() if not slave['external']
    )

    for container in client.containers:
        img = client.container_image(container)
        if img in slave_images:
            status("Removing slave container of", img)
            client.remove_container(container)


