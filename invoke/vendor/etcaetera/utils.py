from .formatters import environ
from .exceptions import MalformationError


def format_key(key):
    return environ(key)


def is_nested_key(key):
    if (key.startswith('.') or
        key.endswith('.') or
        '..' in key):
        raise MalformationError 

    return '.' in key
