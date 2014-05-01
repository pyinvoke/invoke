import os, sys
from contextlib import contextmanager


support = os.path.join(os.path.dirname(__file__), '_support')

@contextmanager
def support_path():
    sys.path.insert(0, support)
    yield
    sys.path.pop(0)

def load(name):
    with support_path():
        return __import__(name)
