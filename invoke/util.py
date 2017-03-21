from contextlib import contextmanager
import io
import logging
import os
import threading
import sys

from .exceptions import ExceptionWrapper


LOG_FORMAT = "%(name)s.%(module)s.%(funcName)s: %(message)s"

def enable_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
    )

# Allow from-the-start debugging (vs toggled during load of tasks module) via
# shell env var.
if os.environ.get('INVOKE_DEBUG'):
    enable_logging()

# Add top level logger functions to global namespace. Meh.
log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)


def sort_names(names):
    """
    Sort task ``names`` by nesting depth & then as regular strings.
    """
    return sorted(names, key=lambda x: (x.count('.'), x))


# TODO: Make part of public API sometime
@contextmanager
def cd(where):
    cwd = os.getcwd()
    os.chdir(where)
    try:
        yield
    finally:
        os.chdir(cwd)


def has_fileno(stream):
    """
    Cleanly determine whether ``stream`` has a useful ``.fileno()``.

    .. note::
        This function helps determine if a given file-like object can be used
        with various terminal-oriented modules and functions such as `select`,
        `termios`, and `tty`. For most of those, a fileno is all that is
        required; they'll function even if ``stream.isatty()`` is ``False``.

    :param stream: A file-like object.

    :returns:
        ``True`` if ``stream.fileno()`` returns an integer, ``False`` otherwise
        (this includes when ``stream`` lacks a ``fileno`` method).
    """
    try:
        return isinstance(stream.fileno(), int)
    except (AttributeError, io.UnsupportedOperation):
        return False


def isatty(stream):
    """
    Cleanly determine whether ``stream`` is a TTY.

    Specifically, first try calling ``stream.isatty()``, and if that fails
    (e.g. due to lacking the method entirely) fallback to `os.isatty`.

    .. note::
        Most of the time, we don't actually care about true TTY-ness, but
        merely whether the stream seems to have a fileno (per `has_fileno`).
        However, in some cases (notably the use of `pty.fork` to present a
        local pseudoterminal) we need to tell if a given stream has a valid
        fileno but *isn't* tied to an actual terminal. Thus, this function.

    :param stream: A file-like object.

    :returns:
        A boolean depending on the result of calling ``.isatty()`` and/or
        `os.isatty`.
    """
    # If there *is* an .isatty, ask it.
    if hasattr(stream, 'isatty') and callable(stream.isatty):
        return stream.isatty()
    # If there wasn't, see if it has a fileno, and if so, ask os.isatty
    elif has_fileno(stream):
        return os.isatty(stream.fileno())
    # If we got here, none of the above worked, so it's reasonable to assume
    # the darn thing isn't a real TTY.
    return False


class ExceptionHandlingThread(threading.Thread):
    """
    Thread handler making it easier for parent to handle thread exceptions.

    Based in part on Fabric 1's ThreadHandler. See also Fabric GH issue #204.

    When used directly, can be used in place of a regular ``threading.Thread``.
    If subclassed, the subclass must do one of:

    - supply ``target`` to ``__init__``
    - define ``_run()`` instead of ``run()``

    This is because this thread's entire point is to wrap behavior around the
    thread's execution; subclasses could not redefine ``run()`` without
    breaking that functionality.
    """
    def __init__(self, **kwargs):
        """
        Create a new exception-handling thread instance.

        Takes all regular `threading.Thread` keyword arguments, via
        ``**kwargs`` for easier display of thread identity when raising
        captured exceptions.
        """
        super(ExceptionHandlingThread, self).__init__(**kwargs)
        # No record of why, but Fabric used daemon threads ever since the
        # switch from select.select, so let's keep doing that.
        self.daemon = True
        # Track exceptions raised in run()
        self.kwargs = kwargs
        self.exc_info = None

    def run(self):
        try:
            # Allow subclasses implemented using the "override run()'s body"
            # approach to work, by using _run() instead of run(). If that
            # doesn't appear to be the case, then assume we're being used
            # directly and just use super() ourselves.
            if hasattr(self, '_run') and callable(self._run):
                # TODO: this could be:
                # - io worker with no 'result' (always local)
                # - tunnel worker, also with no 'result' (also always local)
                # - threaded concurrent run(), sudo(), put(), etc, with a
                # result (not necessarily local; might want to be a subproc or
                # whatever eventually)
                # TODO: so how best to conditionally add a "capture result
                # value of some kind"?
                # - update so all use cases use subclassing, add functionality
                # alongside self.exception() that is for the result of _run()
                # - split out class that does not care about result of _run()
                # and let it continue acting like a normal thread (meh)
                # - assume the run/sudo/etc case will use a queue inside its
                # worker body, orthogonal to how exception handling works
                self._run()
            else:
                super(ExceptionHandlingThread, self).run()
        except BaseException:
            # Store for actual reraising later
            self.exc_info = sys.exc_info()
            # And log now, in case we never get to later (e.g. if executing
            # program is hung waiting for us to do something)
            msg = "Encountered exception {0!r} in thread for {1!r}"
            # Name is either target function's dunder-name, or just "_run" if
            # we were run subclass-wise.
            name = '_run'
            if 'target' in self.kwargs:
                name = self.kwargs['target'].__name__
            debug(msg.format(self.exc_info[1], name)) # noqa

    def exception(self):
        """
        If an exception occurred, return an `.ExceptionWrapper` around it.

        :returns:
            An `.ExceptionWrapper` managing the result of `sys.exc_info`, if an
            exception was raised during thread execution. If no exception
            occurred, returns ``None`` instead.
        """
        if self.exc_info is None:
            return None
        return ExceptionWrapper(self.kwargs, *self.exc_info)

    @property
    def is_dead(self):
        """
        Returns ``True`` if not alive and has a stored exception.

        Used to detect threads that have excepted & shut down.
        """
        # NOTE: it seems highly unlikely that a thread could still be
        # is_alive() but also have encountered an exception. But hey. Why not
        # be thorough?
        return (not self.is_alive()) and self.exc_info is not None

    def __repr__(self):
        # TODO: beef this up more
        return self.kwargs['target'].__name__
