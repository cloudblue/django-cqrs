#!/usr/bin/env python

#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "replica_settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
