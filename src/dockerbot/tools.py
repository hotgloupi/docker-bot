from __future__ import absolute_import
from __future__ import print_function
from __future__ import with_statement

from .log import warn

import pkg_resources as pkg
import os

def copy_resource(name, dest_dir, overwrite = True, dest_name = None):
    if dest_name is None:
        dest_name = name
    dest = os.path.join(dest_dir, dest_name)
    if not overwrite and os.path.exists(dest):
        warn("The buildbot config file", dest, 'exists, creating', dest + '.new', 'instead')
        dest = dest + '.new'
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # XXX Apparently, in an archive, the src does not have an '__exit__' attribute,
    # making it incompatible with a with statement
    src = pkg.resource_stream('dockerbot.data', name)
    try:
        with open(dest, 'w') as out:
            out.write(src.read())
    finally:
        src.close()
