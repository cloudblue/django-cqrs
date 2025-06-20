#  Copyright © 2025 CloudBlue Inc. All rights reserved.

import os


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass
