import os


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass
