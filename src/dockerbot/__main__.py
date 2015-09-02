from __future__ import absolute_import
from __future__ import print_function

import argparse
import sys
import os

from . import command
from . import log
from .error import Error

DESCRIPTION = """
Create and manage docker-bot instances
"""

# Global parser ###############################################################
parser = argparse.ArgumentParser(
    prog = 'dockerbot',
    usage = '<command> [options]',
    description = DESCRIPTION
)

# Common parser ###############################################################
common_parser = argparse.ArgumentParser(add_help = False)

common_parser.add_argument(
    '-f', '--force',
    action = 'store_true',
    help = 'Try harder to achieve your wishes',
)

common_parser.add_argument(
    '-d', '--debug',
    action = 'store_true',
    help = 'Enable debug output',
)

common_parser.add_argument(
    'project_directory',
    nargs = '?',
    help = 'Path to the docker-bot config directory',
)

# Subparsers ##################################################################
subparsers = parser.add_subparsers(help = 'command')


# create command parser #######################################################
create_parser = subparsers.add_parser(
    'create',
    help = 'create a new docker-bot directory',
    parents = [common_parser],
)


# Start command parser ########################################################
start_parser = subparsers.add_parser(
    'start',
    help = 'Start a dockerbot instance',
    parents = [common_parser],
)

start_parser.add_argument(
    'build_directory',
    nargs = '?',
    help = 'Path to the docker-bot build directory',
)

start_parser.add_argument(
    '--console', '-c',
    help = 'Start a console in the buildbot master docker',
    action = 'store_true'
)

start_parser.add_argument(
    '--interactive', '-i',
    help = 'Start the buildbot master in foreground',
    action = 'store_true'
)

# Status command parser #######################################################
status_parser = subparsers.add_parser(
    'status',
    help = 'Check the status',
    parents = [common_parser],
)

status_parser.add_argument(
    'build_directory',
    nargs = '?',
    help = 'Path to the docker-bot build directory',
)


# Parsing arguments
create_parser.set_defaults(func = command.create.main)
start_parser.set_defaults(func = command.start.main)
status_parser.set_defaults(func = command.status.main)

args = vars(parser.parse_args())
main = args.pop('func')
if args.pop('debug'):
    log.LEVEL = log.Level.debug

try:
    main(**args)
except Error:
    e = sys.exc_info()[1]
    print('ERROR:', str(e), file = sys.stderr)
    sys.exit(1)
