from __future__ import print_function

import os
import sys

class Level:
    debug = 0
    info = 1
    warn = 2
    error = 3

LEVEL = Level.info

def error(*args, **kw):
    kw.setdefault('file', sys.stderr)
    print('ERROR:', *args, **kw)

def warn(*args, **kw):
    if LEVEL > Level.warn:
        return
    kw.setdefault('file', sys.stderr)
    print('WARNING:', *args, **kw)

def status(*args, **kw):
    if LEVEL > Level.info:
        return
    kw.setdefault('file', sys.stdout)
    print('-- ', *args, **kw)

def debug(*args, **kw):
    if LEVEL > Level.debug:
        return
    kw.setdefault('file', sys.stderr)
    print('DEBUG:', *args, **kw)


def debug_stream():
    if LEVEL > Level.debug:
        return open(os.devnull, 'w')
    return sys.stderr
