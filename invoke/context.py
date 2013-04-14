from .runner import run


class Context(object):
    """
    Context-aware API wrapper & state-passing object.

    Stores various bits of configuration state internally and uses them to set
    default kwarg values for various API calls, such as `.run`.

    See method call docstrings for additional details.
    """
    def __init__(self, run=None):
        pass

    def run(self, *args, **kwargs):
        return run(*args, **kwargs)
