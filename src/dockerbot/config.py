from __future__ import absolute_import
from __future__ import print_function

import os

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

class Config(object):

    def __init__(self, config_parser):
        self.parser = config_parser

    @classmethod
    def from_file(cls, path):
        parser = cls.make_parser()
        parser.read(path)
        return cls(parser)

    @classmethod
    def from_dir(cls, directory, filename = 'dockerbot.ini'):
        return cls.from_file(os.path.join(directory, filename))

    @classmethod
    def make_parser(cls, *args, **kw):
        return configparser.SafeConfigParser(*args, **kw)


    def _split_key(self, key):
        parts = key.split('.')
        return parts[0], '.'.join(parts[1:])

    def __getitem__(self, full_key):
        section, key = self._split_key(full_key)
        if not self.parser.has_option(section, key):
            raise KeyError(full_key)
        return self.parser.get(section, key)

    def __setitem__(self, full_key, value):
        section, key = self._split_key(full_key)
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        return self.parser.set(section, key, value)
