from __future__ import print_function

import sys

def warn(*args, **kw):
    kw.setdefault('file', sys.stderr)
    print('WARNING:', *args, **kw)
