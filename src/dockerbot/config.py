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
    if project.get('domain') is None:
        raise Error("Missing 'project.domain' key in config file")

    master = cfg.setdefault('master', {})
    db = master.setdefault('database', {})
    db.setdefault('url', 'sqlite:///state.sqlite')

    reporters = master.setdefault('reporters', [])

    slave_defaults = cfg.get('slave-defaults', {})
    for name, slave in cfg['slaves'].items():
        for k, v in slave_defaults.items():
            slave.setdefault(k, deepcopy(v))
        is_external = slave.get('external', not bool(slave.get('docker-file')))
        slave['external'] = is_external
        if not is_external:
            slave.setdefault('volumes', []).extend([
                'slave/%s/root:/buildslave' % name,
                'slave/%s/tmp:/tmp' % name,
            ])

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

        slave.setdefault('dns', [])
        if not isinstance(slave['dns'], list):
            raise Error(
                "dns option should be a list, got %s" % slave['dns']
            )
        # Make sure that each slave has an env
        slave.setdefault('env', {})
        slave['env']['SLAVE'] = name
        if not is_external:
            slave.setdefault('idle-timeout', 600)
            slave.setdefault('image-name', '%s-build-%s' % (project['name'], name))
        slave['password-fixed'] = 'password' in slave
        slave.setdefault(
            'password',
            '%s-%s-%s' % (project['name'], name, random.randint(0, 10000000000))
        )

    for name, repository in cfg['repositories'].items():
        repository['name'] = name
        if repository.get('branch'):
            if repository.get('branch-filter'):
                raise Error("Cannot set both repositories.branch and repositories.branch-filter")
            repository['branch-filter'] = {
                'allow': [{'is': repository.pop('branch')}]
            }
        elif repository.get('branch-filter') is None:
            repository['branch-filter'] = {
                'allow': [{'match': '.*'}]
            }

        repository.setdefault('branch', 'master')
        repository.setdefault('poll-interval', 30)

    for name, build in cfg['builds'].items():
        repository_name = build.get('repository', name)
        if repository_name not in cfg['repositories']:
            raise Error("Repository '%s' is not present in the repositories section" %
                        repository_name)
        build['repository'] = deepcopy(cfg['repositories'][repository_name])
        build['repository']['name'] = repository_name
        build.setdefault('env', {})
        if build.get('branch-filter'):
            build['repository']['branch-filter'] = build.pop('branch-filter')

        if 'variants' not in build:
            build['variants'] = {'default': {'name': name}}

        for variant_name, variant in build['variants'].items():
            variant.setdefault('name', '%s-%s' % (name, variant_name))
            variant.setdefault('slaves', build.get('slaves'))
            variant.setdefault('steps', build.get('steps'))
            variant.setdefault('artifacts', build.get('artifacts', []))
            variant.setdefault('upload-artifacts', build.get('upload-artifacts', []))
            variant['repository'] = deepcopy(build['repository'])
            if variant.get('branch-filter'):
                variant['repository']['branch-filter'] = variant.pop('branch-filter')
            env = {}
            env.update(build['env'])
            env.update(variant.get('env', {}))
            variant['env'] = env
            for k in ('slaves', 'steps'):
                if not variant[k]:
                    raise Error("Build variant %s does not have any %s" % (variant['name'], k))

    return cfg
