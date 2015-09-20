from __future__ import absolute_import
from __future__ import print_function

from .stop import main as stop
from .start import main as start

def main(force, build_directory, console, follow):
    stop(force = force, build_directory = build_directory)
    start(
        force = force,
        project_directory = None,
        build_directory = build_directory,
        console = console,
        follow = follow
    )
