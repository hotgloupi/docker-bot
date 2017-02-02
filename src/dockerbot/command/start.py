from __future__ import absolute_import
from __future__ import print_function

from .. import config
from .. import docker

from ..error import Error
from ..log import warn, status, debug_stream
from ..tools import copy_resource

import io
import json
import os
import random
import shutil
import stat
import subprocess
import sys
import tempfile
import getpass
import pipes

def replace_dir(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def link_dir(src, dst):
    if not os.path.exists(dst):
        os.symlink(src, dst)
    if not os.path.islink(dst):
        raise Error("%s should be a symlink (try to remove it manually)" % dst)

def file_content(path, **kw):
    with open(path) as f:
        return f.read().format(**kw)


BUILDSLAVE_PACKAGES = [
    'buildbot-worker==0.9.1',
    'twisted==15.4.0',
]

BUILDMASTER_PACKAGES = [
    'six>=1.9.0',
    'docker-py',
    'requests',
    'buildbot==0.9.1',
    'buildbot-www==0.9.1',
    'buildbot-waterfall-view==0.9.1',
    'buildbot-console-view==0.9.1',
]

def main(force, project_directory, build_directory, console, follow):
    if build_directory is None:
        build_directory = os.getcwd()
    build_directory = os.path.abspath(build_directory)
    marker = os.path.join(build_directory, '.dockerbot-build')
    if os.path.exists(build_directory):
        ls = os.listdir(build_directory)
        if ls and '.dockerbot-build' not in ls:
            raise Error("%s is not empty and is not an existing build dir" %
                        build_directory)
    else:
        os.makedirs(build_directory)

    if project_directory is None:
        if os.path.exists(marker):
            with open(marker) as f:
                project_directory = f.read().strip()
        else:
            raise Error("Please specify a project directory when building for the first time")
    project_directory = os.path.abspath(project_directory)

    status('Starting project', project_directory, 'in', build_directory)
    config_file = os.path.join(project_directory, 'dockerbot.yml')
    if not os.path.exists(config_file):
        raise Error("The config file '%s' is missing" % config_file)

    with open(marker, 'w') as f: f.write(project_directory)

    cfg = config.load(build_directory, config_file)
    for name, slave in cfg['slaves'].items():
        for volume in slave.get('volumes', []):
            parts = volume.split(':')
            src, dst = parts[0:2]
            if not os.path.exists(src):
                os.makedirs(src)
                #os.chmod(src, stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)

    buildbot_root = os.path.join(build_directory, 'master/root')

    client = docker.Client()

    master_container_path = os.path.abspath(
        os.path.join(build_directory, 'master.container')
    )
    if os.path.exists(master_container_path):
        status('Cleaning up old master container')
        with open(master_container_path) as f:
            container_id = f.read().strip()
        if container_id in client.containers:
            if client.is_container_alive(container_id):
                if not force:
                    raise Error(
                        "Master is already running in %s (use -f to force)" %
                        container_id
                    )
                client.stop_container(container_id)
            else:
                warn("Removing dead master container", container_id)
            client.remove_container(container_id)
        else:
            warn('Cannot find', container_id)
        os.unlink(master_container_path)

    twisted_pidfile = os.path.join(buildbot_root, 'twistd.pid')
    if os.path.exists(twisted_pidfile):
        os.unlink(twisted_pidfile)
    copy_resource('master.cfg', buildbot_root)
    copy_resource('dockerslave.py', buildbot_root)

    with open(os.path.join(project_directory, 'master/Dockerfile')) as src:
        gid = os.stat(cfg['master']['docker-socket'])[stat.ST_GID]
        master_dockerfile = src.read().format(
            user = 'buildmaster',
            uid = os.getuid(),
            gid = gid,
            buildmaster_packages = ' '.join(map(pipes.quote, BUILDMASTER_PACKAGES)),
        )

    master_client = docker.Client(
        volumes = cfg['master'].get('volumes', []) + [
            "%s:/var/run/docker.sock" % cfg['master']['docker-socket'],
            "%s:/buildmaster" % buildbot_root,
            "%s:/steps" % os.path.join(project_directory, 'steps'),
            "%s:/keys" % os.path.join(project_directory, 'keys'),
            "%s:/artifacts" % os.path.join(build_directory, 'artifacts'),
        ],
        ports = [
            "%s:8010" % cfg['master']['www-port'],
            "%s:9989" % cfg['master']['server-port'],
        ],
        cwd = '/buildmaster',
        image_name = cfg['master']['image-name'],
        remove = True,
        pty = True,
    )

    image_id = client.image_id(cfg['master']['image-name'])
    if not image_id or force:
        status("Creating master image '%s'" % cfg['master']['image-name'])
        with tempfile.TemporaryFile() as f:
            f.write(master_dockerfile)
            f.flush()
            f.seek(0)
            client.cmd(
                'build', '-t', cfg['master']['image-name'], '-',
                stdin = f,
            )

    for name, slave in cfg['slaves'].items():
        if slave['password-fixed'] and not force and client.image_id(slave['image-name']):
            status("Using already built slave image", slave['image-name'])
            continue
        if slave['external']:
            continue
        dockerfile = file_content(
            os.path.join(project_directory, slave['docker-file']),
            master_hostname = '%(server-address)s:%(server-port)s' % cfg['master'],
            slave_name = name,
            slave_password = slave['password'],
            user = 'buildslave',
            uid = os.getuid(),
            gid = os.getgid(),
            buildslave_packages = ' '.join(map(pipes.quote, BUILDSLAVE_PACKAGES)),
        )
        status("Creating slave image", slave['image-name'])
        with tempfile.TemporaryFile() as f:
            f.write(dockerfile)
            f.flush()
            f.seek(0)
            client.cmd(
                'build', '-t', slave['image-name'], '-',
                host = slave['docker-host'],
                stdin = f,
                remove = False,
            )

    if not os.path.exists(os.path.join(buildbot_root, 'buildbot.tac')):
        status("Creating the buildbot master in", buildbot_root)
        master_client.cmd(
            'run', "buildbot", "create-master",
            '--db=%s' % cfg['master']['database']['url'], '.',
            remove = True,
            cwd = '/buildmaster',
        )

    for step_dir in ('slaves',):
        replace_dir(
            os.path.join(project_directory, step_dir),
            os.path.join(buildbot_root, step_dir)
        )


    with open(os.path.join(buildbot_root, 'config.json'), 'w') as f:
        json.dump(cfg, f, indent = 4)

    if console:
        try:
            master_client.cmd(
                'run',
       #         '--cidfile', master_container_path,
       #         '-v', '%s:/container.id' % master_container_path,
                'bash',
            )
            retcode = 0
        except:
            retcode = 1
        sys.exit(retcode)

    if follow:
        status("Following build master logs")
        log = os.path.join(buildbot_root, 'twistd.log')
        subprocess.check_call(['touch', log])
        tailf = subprocess.Popen(['tail', '-n0', '-f', log])
    id = master_client.cmd_output(
        'run', 'buildbot', 'start', '--nodaemon', '.',
        extra_volumes = ['%s:/container.id' % master_container_path],
        remove = False,
        daemon = True,
        pty = False,
        cidfile = master_container_path,
    ).strip()
    status("Started buildbot master in", id)

    if follow:
        try:
            tailf.wait()
        except KeyboardInterrupt:
            pass
