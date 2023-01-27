import django
from django.conf import settings


def define_env(env):
    """
    This is the hook for defining variables, macros and filters

    - variables: the dictionary that contains the environment variables
    - macro: a decorator function, to declare a macro.
    - filter: a function with one of more arguments,
        used to perform a transformation
    """
    if not settings.configured:
        settings.configure(DEBUG=True)
        django.setup()
