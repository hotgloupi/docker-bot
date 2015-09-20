from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess

from ..error import Error
from ..log import warn, status, debug_stream

def main(force, build_directory):
    if build_directory is None:
        build_directory = os.getcwd()
    build_directory = os.path.abspath(build_directory)
    marker = os.path.join(build_directory, '.dockerbot-build')
    if not os.path.exists(marker):
        raise Error("%s is not a valid dockerbot build directory" % build_directory)

    master_container_path = os.path.abspath(os.path.join(build_directory, 'master.container'))
    if os.path.exists(master_container_path):
        with open(master_container_path) as f:
            container_id = f.read().strip()
        containers = subprocess.check_output(['docker', 'ps', '-a', '-q', '--no-trunc']).strip().split('\n')
        if container_id in containers:
            state = subprocess.check_output(['docker', 'inspect', '-f', '{{.State.Running}}', container_id]).strip()
            if state == 'true':
                status('Stopping the master container')
                subprocess.call(['docker', 'stop', container_id], stdout = debug_stream())
            status('Removing the master container')
            state = subprocess.call(['docker', 'rm', '-f', container_id], stdout = debug_stream())
        else:
            warn('Cannot find', container_id)
        os.unlink(master_container_path)
