from __future__ import absolute_import
from __future__ import print_function

import subprocess
import copy

from .error import Error
from .log import warn, status, debug, debug_stream

# Common docker actions are factorized here.
# (This is not an attempt to replace the docker-py module)
class Client(object):

    def __init__(self, output_stream = None, **options):
        if output_stream is None:
            output_stream = debug_stream()
        self.output_stream = output_stream
        self.__options = options
        self._to_flags(**self.__options) # Ensure correct options

    def is_container_alive(self, id):
        return id in self.alive_containers

    def has_container(self, id):
        return id in self.containers

    def image_id(self, image_name):
        image_id = self.cmd_output('images', '-q', '--no-trunc', image_name).strip()
        if not image_id: return None
        return image_id

    @property
    def containers(self):
        return filter(None, self.cmd_output('ps', '-a', '-q', '--no-trunc').split('\n'))

    @property
    def alive_containers(self):
        return filter(None, self.cmd_output('ps', '-q', '--no-trunc').split('\n'))

    def container_image(self, id):
        return filter(None, self.cmd_output('inspect', '-f', '{{.Config.Image}}', id).strip())

    @property
    def images(self):
        return filter(None, self.cmd_output('images', '-q', '--no-trunc').split('\n'))

    def stop_container(self, id):
        self.cmd('stop', id)

    def remove_container(self, id):
        self.cmd('rm', '-f', id)

    def cmd(self, cmd, *args, **kw):
        stdin = kw.pop('stdin', None)
        host_cwd = kw.pop('host_cwd', None)
        pre, post = self._to_flags(**kw)
        debug("DOCKER:", ['docker'] + pre + [cmd] + post + list(args))
        subprocess.check_call(
            ['docker'] + pre + [cmd] + post + list(args),
            stdin = stdin,
            stdout = self.output_stream,
            stderr = self.output_stream,
            cwd = host_cwd,
        )

    def cmd_output(self, cmd, *args, **kw):
        stdin = kw.pop('stdin', None)
        host_cwd = kw.pop('host_cwd', None)
        pre, post = self._to_flags(**kw)
        debug("DOCKER:", ['docker'] + pre + [cmd] + post + list(args))
        return subprocess.check_output(
            ['docker'] + pre + [cmd] + post + list(args),
            stdin = stdin,
            cwd = host_cwd,
        ).strip()

    def _to_flags(self, **kw):
        kw = copy.deepcopy(kw)
        for k, v in self.__options.items():
            kw.setdefault(k, v)
        return self.__to_flags(**kw)

    def __to_flags(self,
                   volumes = [],
                   extra_volumes = [],
                   ports = [],
                   cwd = None,
                   pty = False,
                   image_name = None,
                   remove = False,
                   daemon = False,
                   cidfile = None,
                   host = None,
                   dns = [],
    ):
        pre, post = [], []
        if host is not None:
            pre.extend(['-H', host])
        if remove:
            post.append('--rm')
        if dns is not None:
            for addr in dns:
                post.extend(('--dns', addr))
        for volume in volumes:
            post.extend(('-v', volume))
        for volume in extra_volumes:
            post.extend(('-v', volume))
        for port in ports:
            post.extend(('-p', port))
        if cwd is not None:
            post.extend(('-w', cwd))
        if daemon:
            post.append('-d')
        if cidfile is not None:
            post.extend(('--cidfile', cidfile))
        if pty:
            post.append('-ti')
        if image_name is not None:
            post.append(image_name)
        return pre, post

