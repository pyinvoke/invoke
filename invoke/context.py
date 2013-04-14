from .runner import run


class Context(object):
    """
    Context-aware API wrapper & state-passing object.

    Stores various bits of configuration state and uses them to set default
    kwarg values for its wrappers to API calls such as `.Context.run`.

    See method call docstrings for additional details.
    """
    def __init__(self, run=None):
        self.config = {
            'run': run or {}
        }

    def run(self, *args, **kwargs):
        """
        Wrapper for `.run`.

        To set default `.run` keyword argument values, instantiate `.Context`
        with the ``run`` kwarg set to a dict.

        E.g. to create a `.Context` whose `.Context.run` method always defaults
        to ``warn=True``::

            ctx = Context(run={'warn': True})
            ctx.run('command') # behaves like invoke.run('command', warn=True)

        """
        options = dict(self.config['run'])
        options.update(kwargs)
        return run(*args, **options)
