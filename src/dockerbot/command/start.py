from __future__ import absolute_import
from __future__ import print_function

from ..config import Config
from ..error import Error
from ..log import warn
from ..tools import copy_resource

import json
import os
import shutil
import subprocess
import sys


def replace_dir(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def extract_slaves(cfg):
    sections = filter(lambda s: s.startswith('slave.'), cfg.parser.sections())
    if not sections:
        raise Error("No slave has been declared")

    slave_default = {
        'docker-host': 'unix://' + cfg['global.docker-socket'],
        'docker-file': None,
    }
    slaves = {}
    for section in sections:
        slave = {}
        for k, default in slave_default.items():
            value = default
            if cfg.parser.has_option(section, k):
                value = cfg.parser.get(section, k)
            if value is None:
                raise Error("Section '%s' must provide a '%s' value" % (section, k))
            slave[k] = value
        slaves[section.split('.')[1]] = slave
    return slaves

def extract_builds(cfg):
    sections = filter(lambda s: s.startswith('build.'), cfg.parser.sections())
    if not sections:
        raise Error("No build has been declared")
    builds = {}
    for section in sections:
        name = section.split('.')[1]
        build = dict(cfg.parser.items(section))
        for k in ('slaves', 'steps'):
            if k not in build:
                raise Error("Build '%s' is missing the key '%s'" % (name, k))
            build[k] = build[k].split(' ')
        builds[name] = build

    return builds

def main(force, directory, console):
    cfg = Config.from_dir(directory)
    build_dir = cfg['global.build-directory']
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    buildbot_root = os.path.join(build_dir, 'buildbot')

    master_container_path = os.path.join(build_dir, 'master.container')
    if os.path.exists(master_container_path):
        with open(master_container_path) as f:
            container_id = f.read().strip()
        containers = subprocess.check_output(['docker', 'ps', '-a', '-q', '--no-trunc']).strip().split('\n')
        if container_id in containers:
            state = subprocess.check_output(['docker', 'inspect', '-f', '{{.State.Running}}', container_id])
            if state == 'true':
                raise Error("Already running in %s" % f.read().strip())
            warn("Removing dead master container", container_id)
            state = subprocess.call(['docker', 'rm', '-f', container_id])
        else:
            warn('Cannot find', container_id)
        os.unlink(master_container_path)

    copy_resource('master.cfg', buildbot_root)
    copy_resource('dockerslave.py', buildbot_root)

    copy_resource('buildbot.conf', build_dir)
    with open(os.path.join(directory, 'master/Dockerfile')) as src:
        with open(os.path.join(build_dir, 'Dockerfile'), 'w') as dst:
            dst.write(src.read())

    subprocess.check_call(
        ['docker', 'build', '-t', 'buildbot-master', '.'],
        cwd = build_dir,
    )

    options = [
        "-p", "%s:8010" % cfg['master.www-port'],
        "-p", "%s:9989" % cfg['master.server-port'],
        "-v", "%s:/var/run/docker.sock" % cfg['global.docker-socket'],
        "-v", "%s:/data/buildbot/master" % buildbot_root,
        "-w", "/data/buildbot/master",
        cfg['master.image-name']
    ]

    if not os.path.exists(os.path.join(buildbot_root, 'buildbot.tac')):
        subprocess.check_call(
            ['docker', 'run', '-t'] + options +
            ["buildbot", "create-master", '.']
        )

    for dir in ('slaves', 'steps'):
        replace_dir(
            os.path.join(build_dir, dir),
            os.path.join(buildbot_root, dir)
        )

    description = {
        'master': dict(cfg.parser.items('master')),
        'slaves': extract_slaves(cfg),
        'builds': extract_builds(cfg),
        'repository': {
            'url': cfg['repository.url'],
        }
    }
    with open(os.path.join(buildbot_root, 'description.json'), 'w') as f:
        json.dump(description, f)

    if console:
        sys.exit(
            subprocess.call(
                ['docker', 'run', '--rm', '-ti'] + options + ['bash'],
            )
        )
    else:
        with open(master_container_path, 'w') as f:
            id = subprocess.check_output(
                ['docker', 'run', '-d'] + options +
                ['twistd', '--nodaemon', '--no_save', '-y', 'buildbot.tac'],
            )
            print("Started buildbot master in", id)
            f.write(id)
