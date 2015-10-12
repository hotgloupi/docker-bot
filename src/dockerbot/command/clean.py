from __future__ import absolute_import
from __future__ import print_function

from .. import docker
from ..log import status

def main(force, build_directory, orphan_images, dead_containers):
    client = docker.Client()
    if dead_containers:
        all_containers, alive_containers = client.containers, client.alive_containers
        for container in all_containers:
            if container not in alive_containers:
                status("Removing dead container", container)
                client.remove_container(container)

    if orphan_images:
        images = client.cmd_output(
            'images', '-a', '-q', '--no-trunc', '--filter', 'dangling=true'
        ).split('\n')
        for image in images:
            if not image: continue
            status("Removing image", image)
            client.cmd('rmi', image)
