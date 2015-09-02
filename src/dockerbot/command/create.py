from __future__ import absolute_import
from __future__ import print_function
from __future__ import with_statement

import os
import pkg_resources as pkg
import socket

import yaml

from ..tools import copy_resource
from ..error import Error
from ..config import Config
from ..log import warn

import yaml

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def main(project_directory, force):
    if project_directory is None:
        project_directory = os.getcwd()
    if not os.path.exists(project_directory):
        os.makedirs(project_directory)
    elif not force:
        raise Error("The directory '%s' already exists, use -f to force" % project_directory)

    copy_resource('dockerbot.yml', project_directory, dest_name = 'dockerbot.yml.sample')

    sample_path = os.path.join(project_directory, 'dockerbot.yml.sample')
    with open(sample_path) as f:
        cfg = yaml.load(f)
    cfg['master']['server-address'] = get_ip_address()
    with open(sample_path, 'w') as f:
        yaml.dump(cfg, stream = f, default_flow_style = False)

    copy_resource(
        'master.dockerfile',
        os.path.join(project_directory, 'master'),
        dest_name = 'Dockerfile'
    )
    slaves_dir = os.path.join(project_directory, 'slaves')
    if os.path.exists(slaves_dir):
        warn(slaves_dir, 'already there, leaving untouched')
    else:
        copy_resource(
            'slave-sample.dockerfile',
            slaves_dir,
            dest_name = 'sample.dockerfile'
        )

    steps_dir = os.path.join(project_directory, 'steps')
    if os.path.exists(steps_dir):
        warn(steps_dir, 'already there, leaving untouched')
    else:
        for step in ('setup.sh', 'build.sh'):
            copy_resource(
                step,
                steps_dir,
            )
    config = os.path.join(project_directory, 'dockerbot.yml')
    if not os.path.exists(config):
        print("Please copy {0}.sample to {0} and edit it to fit your needs".format(config))

