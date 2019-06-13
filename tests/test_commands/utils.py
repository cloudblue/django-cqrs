from __future__ import unicode_literals

import os


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass
