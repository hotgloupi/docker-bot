from __future__ import absolute_import
from __future__ import print_function

from ..config import Config
from ..error import Error
from ..log import warn, status, debug_stream
from ..tools import copy_resource
import yaml

import json
import os
import shutil
import subprocess
import sys

def replace_dir(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def main(force, project_directory, build_directory, console, interactive):
    status('Starting project', project_directory, 'in', build_directory)
    if build_directory is None:
        build_directory = os.getcwd()
    build_directory = os.path.abspath(build_directory)
    marker = os.path.join(build_directory, '.dockerbot-build')
    if os.path.exists(build_directory):
        ls = os.listdir(build_directory)
        if ls and '.dockerbot-build' not in ls:
            raise Error("%s is not empty and is not an existing build dir" % build_directory)
    else:
        os.makedirs(build_directory)

    if project_directory is None:
        if os.path.exists(marker):
            with open(marker) as f:
                project_directory = f.read().strip()
        else:
            raise Error("Please specify a project directory when building for the first time")

    project_directory = os.path.abspath(project_directory)
    config_file = os.path.join(project_directory, 'dockerbot.yml')
    if not os.path.exists(config_file):
        raise Error("The config file '%s' is missing" % config_file)

    with open(marker, 'w') as f: f.write(project_directory)

    cfg = yaml.load(open(config_file))

    buildbot_root = os.path.join(build_directory, 'buildbot')

    master_container_path = os.path.join(build_directory, 'master.container')
    if os.path.exists(master_container_path):
        status('Cleaning up old master container')
        with open(master_container_path) as f:
            container_id = f.read().strip()
        containers = subprocess.check_output(['docker', 'ps', '-a', '-q', '--no-trunc']).strip().split('\n')
        if container_id in containers:
            state = subprocess.check_output(['docker', 'inspect', '-f', '{{.State.Running}}', container_id])
            if state == 'true':
                raise Error("Already running in %s" % f.read().strip())
            warn("Removing dead master container", container_id)
            state = subprocess.call(['docker', 'rm', '-f', container_id], stdout = debug_stream())
        else:
            warn('Cannot find', container_id)
        os.unlink(master_container_path)

    twisted_pidfile = os.path.join(buildbot_root, 'twistd.pid')
    if os.path.exists(twisted_pidfile):
        os.unlink(twisted_pidfile)
    copy_resource('master.cfg', buildbot_root)
    copy_resource('dockerslave.py', buildbot_root)

    copy_resource('buildbot.conf', build_directory)
    with open(os.path.join(project_directory, 'master/Dockerfile')) as src:
        with open(os.path.join(build_directory, 'Dockerfile'), 'w') as dst:
            dst.write(src.read())

    options = [
        "-p", "%s:8010" % cfg['master']['www-port'],
        "-p", "%s:9989" % cfg['master']['server-port'],
        "-v", "%s:/var/run/docker.sock" % cfg['master']['docker-socket'],
        "-v", "%s:/data/buildbot/master" % buildbot_root,
        "-w", "/data/buildbot/master",
        cfg['master']['image-name']
    ]
    image_id = subprocess.check_output(['docker', 'images', '-q', '--no-trunc', cfg['master']['image-name']])
    if not image_id or force:
        status("Creating the docker image '%s'" % cfg['master']['image-name'])
        subprocess.check_call(
            ['docker', 'build', '-t', cfg['master']['image-name'], '.'],
            cwd = build_directory,
            stdout = debug_stream(),
            stderr = debug_stream(),
        )


    if not os.path.exists(os.path.join(buildbot_root, 'buildbot.tac')):
        status("Creating the buildbot master in", buildbot_root)
        subprocess.check_call(
            ['docker', 'run', '--rm', '-t'] + options +
            ['chown', '-R', '{u}:{g}'.format(u = os.getuid(), g = os.getgid()), '.'],
            stdout = debug_stream(),
        )
        subprocess.check_call(
            ['docker', 'run', '--rm', '-t'] + options +
            ["buildbot", "create-master", '.'],
            stdout = debug_stream(),
        )
        subprocess.check_call(
            ['docker', 'run', '--rm', '-t'] + options +
            ['chown', '-R', '{u}:{g}'.format(u = os.getuid(), g = os.getgid()), '.'],
            stdout = debug_stream(),
        )

    subprocess.check_call(
        ['docker', 'run', '--rm', '-t'] + options +
        ['chown', '-R', '{u}:{g}'.format(u = os.getuid(), g = os.getgid()), '.'],
        stdout = debug_stream(),
    )
    for step_dir in ('slaves', 'steps'):
        replace_dir(
            os.path.join(project_directory, step_dir),
            os.path.join(buildbot_root, step_dir)
        )


    with open(os.path.join(buildbot_root, 'config.json'), 'w') as f:
        json.dump(cfg, f)

    if console:
        retcode = subprocess.call(
            ['docker', 'run', '--rm', '-ti'] + options + ['bash'],
        )
        subprocess.call(
            ['docker', 'run', '--rm', '-t'] + options +
            ['chown', '-R', '{u}:{g}'.format(u = os.getuid(), g = os.getgid()), '.'],
            stdout = debug_stream(),
        )
        sys.exit(retcode)

    if interactive:
        status("Starting buildbot master in forground")
        subprocess.check_call(
            ['docker', 'run', '--rm', '-ti'] +
            options +
            #['twistd', '--nodaemon', '--no_save', '-y', 'buildbot.tac'],
            ['buildbot', 'start', '.']
        )
    else:
        id = subprocess.check_output(
            ['docker', 'run', '-d'] +
            options +
            #['twistd', '--nodaemon', '--no_save', '-y', 'buildbot.tac'],
            ['buildbot', 'start', '--nodaemon', '.']
        ).strip()
        status("Started buildbot master in", id)
        with open(master_container_path, 'w') as f:
            f.write(id)
