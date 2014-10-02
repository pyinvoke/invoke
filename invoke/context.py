from copy import deepcopy

from .runner import run
from .config import Config, DataProxy


class Context(DataProxy):
    """
    Context-aware API wrapper & state-passing object.

    `.Context` objects are created during command-line parsing (or, if desired,
    by hand) and used to share parser and configuration state with executed
    tasks (see :doc:`/concepts/context`).

    Specifically, the class offers wrappers for core API calls (such as `.run`)
    which take into account CLI parser flags, configuration files, and/or
    changes made at runtime. It also acts as a proxy for its `~.Context.config`
    attribute - see that attribute's documentation for details.

    Instances of `.Context` may be shared between tasks when executing
    sub-tasks - either the same context the caller was given, or an altered
    copy thereof (or, theoretically, a brand new one).

    .. note::
        Transmitting a copy (using e.g. `.clone`) instead of mutating a
        ``Context`` in-place is a nice way to limit unwanted or hard-to-track
        state mutation, and/or to enable safer concurrency.
    """
    def __init__(self, config=None):
        """
        :param config:
            `.Config` object to use as the base configuration.

            Defaults to an empty `.Config`.
        """
        
        #: The fully merged `.Config` object appropriate for this context.
        #:
        #: `.Config` settings (see their documentation for details) may be
        #: accessed like dictionary keys (``ctx.config['foo']``) or object
        #: attributes (``ctx.config.foo``).
        #:
        #: As a convenience shorthand, the `.Context` object proxies to its
        #: ``config`` attribute in the same way - e.g. ``ctx['foo']`` or
        #: ``ctx.foo`` returns the same value as ``ctx.config['foo']``.
        self.config = config if config is not None else Config()

    def clone(self):
        """
        Return a new Context instance resembling this one.
        """
        return Context(config=self.config.clone())

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

