from __future__ import absolute_import
from __future__ import print_function
from __future__ import with_statement

import os
import pkg_resources as pkg
import socket

from ..tools import copy_resource
from ..error import Error
from ..config import Config

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def main(directory, force, build_directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
    elif not force:
        raise Error("The directory '%s' already exists, use -f to force" % directory)

    if build_directory is None:
        build_directory = os.path.join(directory, '.build')
    build_directory = os.path.abspath(build_directory)

    config_parser = Config.make_parser()
    with pkg.resource_stream('dockerbot.data', 'dockerbot.ini') as src:
        config_parser.readfp(src)

    config = Config(config_parser)
    config['global.build-directory'] = build_directory
    config['master.server-address'] = get_ip_address()

    with open(os.path.join(directory, 'dockerbot.ini'), 'w') as out:
        config_parser.write(out)

    copy_resource(
        'master.dockerfile',
        os.path.join(directory, 'master'),
        dest_name = 'Dockerfile'
    )
    slaves_dir = os.path.join(build_directory, 'slaves')
    copy_resource(
        'slave-sample.dockerfile',
        slaves_dir,
        dest_name = 'sample.dockerfile'
    )

    steps_dir = os.path.join(build_directory, 'steps')
    for step in ('setup.sh', 'build.sh'):
        copy_resource(
            step,
            steps_dir,
            overwrite = False
        )

