from __future__ import absolute_import
from __future__ import print_function

import argparse
import sys
import os

from . import command
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
    'directory',
    help = 'Path to the docker-bot config directory',
)

# Subparsers ##################################################################
subparsers = parser.add_subparsers(help = 'command')


# Init command parser #########################################################
init_parser = subparsers.add_parser(
    'init',
    help = 'Initialize a new docker-bot directory',
    parents = [common_parser],
)

init_parser.add_argument(
    '--build-directory', '-b',
    help = 'Specify a build directory outside of the root directory',
    action = 'store',
)


# Start command parser ########################################################
start_parser = subparsers.add_parser(
    'start',
    help = 'Start a dockerbot instance',
    parents = [common_parser],
)

start_parser.add_argument(
    '--console', '-c',
    help = 'Start a console instead of launching the daemon',
    action = 'store_true'
)

# Parsing arguments
init_parser.set_defaults(func = command.init.main)
start_parser.set_defaults(func = command.start.main)

args = vars(parser.parse_args())
main = args.pop('func')

try:
    main(**args)
except Error:
    e = sys.exc_info()[1]
    print('ERROR:', str(e), file = sys.stderr)
    sys.exit(1)
