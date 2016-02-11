from __future__ import absolute_import
from __future__ import print_function

import yaml
import os
import random
from copy import deepcopy

from .error import Error

def load(build_directory, config_file):
    with open(config_file) as f:
        cfg = yaml.load(f)

    project = cfg.get('project')
    if project is None:
        raise Error("Missing 'project' key in config file")

    slave_defaults = cfg.get('slave-defaults', {})
    for name, slave in cfg['slaves'].items():
        for k, v in slave_defaults.items():
            slave.setdefault(k, deepcopy(v))
        is_external = slave.get('external', not bool(slave.get('docker-file')))
        slave['external'] = is_external
        if not is_external:
            slave.setdefault('volumes', []).append('builds/%s:/buildslave/' % name)
            volumes = []
            for volume in slave['volumes']:
                parts = volume.split(':')
                src, dst = parts[0:2]
                if not os.path.isabs(src):
                    src = os.path.join(build_directory, src)
                if not os.path.isabs(dst):
                    raise Error(
                        ("The volume %s destination mount point of the slave %s is"
                         " not absolute") % (volume, name)
                    )
                volumes.append(':'.join([src, dst] + parts[2:]))
            slave['volumes'] = volumes

        # Make sure that each slave has an env
        slave.setdefault('env', {})
        slave['env']['SLAVE_NAME'] = name
        if not is_external:
            slave.setdefault('idle-timeout', 600)
            slave.setdefault('image-name', '%s-build-%s' % (project, name))
        slave['password-fixed'] = 'password' in slave
        slave.setdefault(
            'password',
            '%s-%s-%s' % (project, name, random.randint(0, 10000000000))
        )

    for name, repository in cfg['repositories'].items():
        repository['name'] = name
        repository.setdefault('branch', 'master')
        repository.setdefault('poll-interval', 30)

    for name, build in cfg['builds'].items():
        repository_name = build.get('repository', name)
        if repository_name not in cfg['repositories']:
            raise Error("Repository '%s' is not present in the repositories section" %
                        repository_name)
        build['repository'] = cfg['repositories'][repository_name]
        build['repository']['name'] = repository_name
        build.setdefault('env', {})

        if 'variants' not in build:
            build['variants'] = {'default': {'name': name}}

        for variant_name, variant in build['variants'].items():
            variant.setdefault('name', '%s-%s' % (name, variant_name))
            variant.setdefault('slaves', build.get('slaves'))
            variant.setdefault('steps', build.get('steps'))
            variant.setdefault('artifacts', build.get('artifacts', []))
            variant.setdefault('upload-artifacts', build.get('upload-artifacts', []))
            env = {}
            env.update(build['env'])
            env.update(variant.get('env', {}))
            variant['env'] = env
            for k in ('slaves', 'steps'):
                if not variant[k]:
                    raise Error("Build variant %s does not have any k" % (variant['name'], k))

    return cfg
