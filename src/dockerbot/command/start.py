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

def link_dir(src, dst):
    if not os.path.exists(dst):
        os.symlink(src, dst)
    if not os.path.islink(dst):
        raise Error("%s should be a symlink (try to remove it manually)" % dst)

def main(force, project_directory, build_directory, console, follow):
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

    status('Starting project', project_directory, 'in', build_directory)
    config_file = os.path.join(project_directory, 'dockerbot.yml')
    if not os.path.exists(config_file):
        raise Error("The config file '%s' is missing" % config_file)

    with open(marker, 'w') as f: f.write(project_directory)

    cfg = yaml.load(open(config_file))

    buildbot_root = os.path.join(build_directory, 'buildbot')

    master_container_path = os.path.abspath(os.path.join(build_directory, 'master.container'))
    if os.path.exists(master_container_path):
        status('Cleaning up old master container')
        with open(master_container_path) as f:
            container_id = f.read().strip()
        containers = subprocess.check_output(['docker', 'ps', '-a', '-q', '--no-trunc']).strip().split('\n')
        if container_id in containers:
            state = subprocess.check_output(['docker', 'inspect', '-f', '{{.State.Running}}', container_id]).strip()
            if state == 'true':
                if not force:
                    raise Error("Master is already running in %s (use -f to force)" % container_id)
                subprocess.call(['docker', 'stop', container_id], stdout = debug_stream())
            else:
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

    volumes = cfg['master'].get('volumes', []) + [
        "%s:/var/run/docker.sock" % cfg['master']['docker-socket'],
        "%s:/buildmaster" % buildbot_root,
        "%s:/steps" % os.path.join(project_directory, 'steps'),
    ]
    options = [
        "-p", "%s:8010" % cfg['master']['www-port'],
        "-p", "%s:9989" % cfg['master']['server-port'],
    ]
    for volume in volumes:
        options += ['-v', volume]

    options += [
        "-w", "/buildmaster",
        cfg['master']['image-name']
    ]
    image_id = subprocess.check_output(['docker', 'images', '-q', '--no-trunc', cfg['master']['image-name']])
    if not image_id or force:
        status("Creating the docker image '%s'" % cfg['master']['image-name'])
        if image_id:
            subprocess.check_call(
                ['docker', 'run', '--rm', '-t'] + options +
                ['chown', '-R', '{u}:{g}'.format(u = os.getuid(), g = os.getgid()), '.'],
                stdout = debug_stream(),
            )
        subprocess.check_call(
            ['docker', 'build', '-t', cfg['master']['image-name'], '.'],
            cwd = build_directory,
            stdout = debug_stream(),
            stderr = debug_stream(),
        )

    for name, slave in cfg['slaves'].items():
        volumes = []
        for volume in slave.get('volumes', []):
            parts = volume.split(':')
            src, dst = parts[0:2]
            if not os.path.isabs(src):
                src = os.path.join(build_directory, src)
            if not os.path.isabs(dst):
                raise Error("The volume %s destination mount point of the slave %s is not absolute" % (volume, name))
            if not os.path.exists(src):
                os.makedirs(src)
            volumes.append(':'.join([src, dst] + parts[2:]))
        slave['volumes'] = volumes


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
    for step_dir in ('slaves',):
        replace_dir(
            os.path.join(project_directory, step_dir),
            os.path.join(buildbot_root, step_dir)
        )


    with open(os.path.join(buildbot_root, 'config.json'), 'w') as f:
        json.dump(cfg, f)

    if console:
        retcode = subprocess.call(
            [
                'docker', 'run', '--rm', '-ti',
                '--cidfile', master_container_path,
                '-v', '%s:/container.id' % master_container_path,
            ] + options + ['bash'],
        )
        subprocess.call(
            ['docker', 'run', '--rm', '-t'] + options +
            ['chown', '-R', '{u}:{g}'.format(u = os.getuid(), g = os.getgid()), '.'],
            stdout = debug_stream(),
        )
        sys.exit(retcode)

    if follow:
        status("Following build master logs")
        tailf = subprocess.Popen(
            ['tail', '-n0', '-f', os.path.join(buildbot_root, 'twistd.log')]
        )
    id = subprocess.check_output(
        [
            'docker', 'run', '-d',
             '--cidfile', master_container_path,
             '-v', '%s:/container.id' % master_container_path,
        ] +
        options +
        #['twistd', '--nodaemon', '--no_save', '-y', 'buildbot.tac'],
        ['buildbot', 'start', '--nodaemon', '.']
    ).strip()
    status("Started buildbot master in", id)

    if follow:
        try:
            tailf.wait()
        except KeyboardInterrupt:
            pass
