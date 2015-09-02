from __future__ import absolute_import
from __future__ import print_function

import sys
if sys.version_info.major < 3:
    from .lib.yaml import *
else:
    from .lib3.yaml import *
