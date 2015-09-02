from __future__ import print_function

import os
import subprocess

def main(project_directory, build_directory, force):
    if build_directory is None:
        build_directory = os.getcwd()
    build_directory = os.path.abspath(build_directory)
    master_container_path = os.path.join(build_directory, 'master.container')
    if os.path.exists(master_container_path):
        with open(master_container_path) as f:
            container_id = f.read().strip()
        containers = subprocess.check_output(['docker', 'ps', '-a', '-q', '--no-trunc']).strip().split('\n')
        if container_id in containers:
            state = subprocess.check_output(['docker', 'inspect', '-f', '{{.State.Running}}', container_id])
            if state == 'true':
                print("docker-bot: running")
            else:
                print("docker-bot: dead")
        else:
            print("docker-bot: dead and removed")
    else:
        print("docker-bot: stopped")
