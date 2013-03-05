import os, sys


support = os.path.join(os.path.dirname(__file__), '_support')

def load(name):
    sys.path.insert(0, support)
    mod = __import__(name)
    sys.path.pop(0)
    return mod
