# -*- coding: utf-8 -*-

import os
from subprocess import Popen, PIPE
import sys
import threading
import codecs
import locale

from .exceptions import Failure
from .platform import WINDOWS

from .vendor import six


def normalize_hide(val):
    hide_vals = (None, False, 'out', 'stdout', 'err', 'stderr', 'both', True)
    if val not in hide_vals:
        err = "'hide' got {0!r} which is not in {1!r}"
        raise ValueError(err.format(val, hide_vals))
    if val in (None, False):
        hide = ()
    elif val in ('both', True):
        hide = ('out', 'err')
    elif val == 'stdout':
        hide = ('out',)
    elif val == 'stderr':
        hide = ('err',)
    else:
        hide = (val,)
    return hide


# TODO: remove 'exception' field in run_* return values, if we don't run into
# situations similar to the one found in pexpect re: spurious IOErrors on Linux
# w/ PTYs. See #37 / 45db03ed8343ac97beefb360634f8106de92c6d7

class Runner(object):
    """
    Partially-abstract core command-running API.

    This class is not usable by itself and must be subclassed to implement, at
    minimum, ``run_direct`` and ``run_pty``. An explanation of its methods
    follows:

    ``run`` is the primary API call which handles high level logic (echoing the
    commands locally, constructing a useful `Result` object, etc) and
    wraps/delegates to the below methods for actual execution.

    ``select_method`` takes ``pty`` and ``fallback`` kwargs and returns the
    current object's ``run_direct`` or ``run_pty`` method, depending on those
    kwargs' values and environmental cues/limitations. `Runner` itself has a
    useful default implementation of this method, but overriding may be
    sometimes necessary.

    ``run_direct`` and ``run_pty`` are fully abstract in `Runner`; in
    subclasses, they should perform actual command execution, hooking directly
    into a subprocess' stdout/stderr pipes and returning those pipes' eventual
    full contents as distinct strings.

    ``run_direct``/``run_pty`` both have a signature of ``(self, command, warn,
    hide, encoding, out_stream, err_stream)`` (see `run` for semantics of
    these) and must return a 4-tuple of ``(stdout, stderr, exitcode,
    exception)`` (see `Result` for their meaning).

    ``run_pty`` differs from ``run_direct`` in that it should utilize a
    pseudo-terminal, and is expected to only return a useful ``stdout`` (with
    ``stderr`` usually set to the empty string.)

    For a subclass implementation example, see the source code for `.Local`.
    """
    def __init__(self, context):
        """
        Create a new runner with a handle on some `.Context`.

        :param context:
            a `.Context` instance, used to transmit default options and provide
            access to other contextualized information (e.g. a remote-oriented
            `.Runner` might want a `.Context` subclass holding info about
            hostnames and ports.)

            .. note::
                The `.Context` given to `.Runner` instances **must** contain
                default config values for the `.Runner` class in question. At a
                minimum, this means values for each of the default
                `.Runner.run` keyword arguments such as ``echo`` and ``warn``.

        :raises exceptions.ValueError:
            if not all expected default values are found in ``context``.
        """
        #: The `.Context` given to the same-named argument of `__init__`.
        self.context = context

    def run(self, command, **kwargs):
        """
        Execute ``command``, returning a `Result` object.

        .. note::
            All kwargs will default to the values found in this instance's
            `~.Runner.context` attribute, specifically in its configuration's
            ``run`` subtree (e.g. ``run.echo`` provides the default value for
            the ``echo`` keyword, etc). The base default values are described
            in the parameter list below.

        :param str command: The shell command to execute.

        :param bool warn:
            Whether to warn and continue, instead of raising `.Failure`, when
            the executed command exits with a nonzero status. Default:
            ``False``.

        :param hide:
            Allows the caller to disable ``run``'s default behavior of copying
            the subprocess' stdout and stderr to the controlling terminal.
            Specify ``hide='out'`` (or ``'stdout'``) to hide only the stdout
            stream, ``hide='err'`` (or ``'stderr'``) to hide only stderr, or
            ``hide='both'`` (or ``True``) to hide both streams.

            The default value is ``None``, meaning to print everything;
            ``False`` will also disable hiding.

            .. note::
                Stdout and stderr are always captured and stored in the
                ``Result`` object, regardless of ``hide``'s value.

        :param bool pty:
            By default, ``run`` connects directly to the invoked process and
            reads its stdout/stderr streams. Some programs will buffer (or even
            behave) differently in this situation compared to using an actual
            terminal or pty. To use a pty, specify ``pty=True``.

            .. warning::
                Due to their nature, ptys have a single output stream, so the
                ability to tell stdout apart from stderr is **not possible**
                when ``pty=True``. As such, all output will appear on
                ``out_stream`` (see below) and be captured into the ``stdout``
                result attribute. ``err_stream`` and ``stderr`` will always be
                empty when ``pty=True``.

        :param bool fallback:
            Controls auto-fallback behavior re: problems offering a pty when
            ``pty=True``. Whether this has any effect depends on the specific
            `Runner` subclass being invoked. Default: ``True``.

        :param bool echo:
            Controls whether `.run` prints the command string to local stdout
            prior to executing it. Default: ``False``.

        :param str encoding:
            Override auto-detection of which encoding the subprocess is using
            for its stdout/stderr streams. Defaults to the return value of
            ``locale.getpreferredencoding(False)``).

        :param out_stream:
            A file-like stream object to which the subprocess' standard error
            should be written. If ``None`` (the default), ``sys.stdout`` will
            be used.

        :param err_stream:
            Same as ``out_stream``, except for standard error, and defaulting
            to ``sys.stderr``.

        :returns: `Result`

        :raises: `.Failure` (if the command exited nonzero & ``warn=False``)
        """
        exception = False
        # Normalize kwargs w/ config
        opts = {}
        for key, value in six.iteritems(self.context.config.run):
            runtime = kwargs.pop(key, None)
            opts[key] = value if runtime is None else runtime
        # TODO: handle invalid kwarg keys (anything left in kwargs)
        # Normalize 'hide' from one of the various valid input values
        opts['hide'] = normalize_hide(opts['hide'])
        # Derive stream objects
        out_stream = opts['out_stream']
        if out_stream is None:
            out_stream = sys.stdout
        err_stream = opts['err_stream']
        if err_stream is None:
            err_stream = sys.stderr
        # Do the things
        if opts['echo']:
            print("\033[1;37m{0}\033[0m".format(command))
        func = self.select_method(pty=opts['pty'], fallback=opts['fallback'])
        stdout, stderr, exited, exception = func(
            command=command,
            warn=opts['warn'],
            hide=opts['hide'],
            encoding=opts['encoding'],
            out_stream=out_stream,
            err_stream=err_stream,
        )
        # TODO: make this test less gross? Feels silly to just return a bool in
        # select_method which is tantamount to this, though.
        func_name = getattr(func, 'func_name', getattr(func, '__name__'))
        used_pty = func_name == 'run_pty'
        result = Result(
            stdout=stdout,
            stderr=stderr,
            exited=exited,
            pty=used_pty,
            exception=exception,
        )
        if not (result or opts['warn']):
            raise Failure(result)
        return result

    def select_method(self, pty, fallback):
        # NOTE: fallback not used: no falling back implemented by default.
        return getattr(self, 'run_pty' if pty else 'run_direct')

    def run_direct(
        self, command, warn, hide, encoding, out_stream, err_stream
    ):
        raise NotImplementedError

    def run_pty(self, command, warn, hide, encoding, out_stream, err_stream):
        raise NotImplementedError


class Local(Runner):
    """
    Execute a command on the local system in a subprocess.

    .. note::
        When Invoke itself is executed without a valid PTY (i.e.
        ``os.isatty(sys.stdin)`` is ``False``), it's not possible to present a
        handle on our PTY to local subprocesses. In such situations, `Local`
        will fallback to behaving as if ``pty=False``, on the theory that
        degraded execution is better than none at all, as well as printing a
        warning to stderr.

        To disable this behavior (i.e. if ``os.isatty`` is causing false
        negatives in your environment), say ``fallback=False``.
    """
    def select_method(self, pty=False, fallback=True):
        func = self.run_direct
        if pty:
            func = self.run_pty
            if not os.isatty(sys.stdin.fileno()) and fallback:
                sys.stderr.write("WARNING: stdin is not a pty; falling back to non-pty execution!\n") # noqa
                func = self.run_direct
        return func

    def _normalize_encoding(self, encoding):
        return locale.getpreferredencoding(False)

    def _mux(self, source_fd, dest, buffer_, hide, encoding):
        # Inner generator yielding read data
        def get():
            while True:
                data = os.read(source_fd, 1000)
                if not data:
                    break
                # Sometimes os.read gives us bytes under Python 3...and
                # sometimes it doesn't. ¯\_(ツ)_/¯
                if not isinstance(data, six.binary_type):
                    # Can't use six.b because that just assumes latin-1 :(
                    data = data.encode(encoding)
                yield data
        # Use generator in iterdecode() to decode stream data, then print/save
        for data in codecs.iterdecode(get(), encoding, errors='replace'):
            if not hide:
                dest.write(data)
                dest.flush()
            buffer_.append(data)

    def _start_threads(self, arg_tuples):
        threads = []

        for args in arg_tuples:
            t = threading.Thread(target=self._mux, args=args)
            threads.append(t)
            t.start()

        return threads

    def _obtain_outputs(self, threads, stdout, stderr):
        for t in threads:
            t.join()

        stdout = ''.join(stdout)
        stderr = ''.join(stderr)
        if WINDOWS:
            # "Universal newlines" - replace all standard forms of
            # newline with \n. This is not technically Windows related
            # (\r as newline is an old Mac convention) but we only apply
            # the translation for Windows as that's the only platform
            # it is likely to matter for these days.
            stdout = stdout.replace("\r\n", "\n").replace("\r", "\n")
            stderr = stderr.replace("\r\n", "\n").replace("\r", "\n")

        return stdout, stderr

    # TODO:
    # * make another subclass, LocalPty (or - two new subclasses?)
    # * invert rundirect/runpty and the new subroutines, making new subroutines
    # out of the bits that are actually different in the current functions
    # * then run_direct/run_pty should be 100% identical and can be merged
    # * meaning updating run()/select_method() at least a small bit to select
    # which class is used, instead of which function
    # * look at fabric to make sure this would still work OK (so the bits
    # changing in fabric, which is largely just executing additional code on
    # startup to request PTY, still fit into this pattern)
    # * make sure no tests need to change to care about any of this
    # * merge to master


    def run_direct(
        self, command, warn, hide, encoding, out_stream, err_stream
    ):
        process = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
        )

        encoding = self._normalize_encoding(encoding)

        stdout, stderr = [], []
        threads = self._start_threads((
            (process.stdout.fileno(), out_stream, stdout, 'out' in hide,
                encoding),
            (process.stderr.fileno(), err_stream, stderr, 'err' in hide,
                encoding),
        ))

        process.wait()

        stdout, stderr = self._obtain_outputs(threads, stdout, stderr)

        return stdout, stderr, process.returncode, None

    def run_pty(self, command, warn, hide, encoding, out_stream, err_stream):
        # TODO: re-insert Windows "lol y u no pty" stuff here
        import pty
        pid, parent_fd = pty.fork()
        # If we're the child process, load up the actual command in a shell,
        # just as subprocess does; this replaces our process - whose pipes are
        # all hooked up to the PTY - with the "real" one.
        if pid == 0:
            # Use execv for bare-minimum "exec w/ variable # args" behavior.
            # No need for the 'p' (use PATH to find executable) or 'e' (define
            # a custom/overridden shell env) variants, for now.
            # TODO: use /bin/sh or whatever subprocess does. Only using bash
            # for now because that's what we have been testing against.
            # TODO: also see if subprocess is using equivalent of execvp...
            # TODO: both pty.spawn() and pexpect.spawn() do a lot of
            # setup/teardown involving tty.*, setwinsize, getrlimit, signal.
            # Ostensibly we'll want some of that eventually, but if possible
            # write tests - integration-level if necessary - before adding it!
            os.execv('/bin/bash', ['/bin/bash', '-c', command])

        encoding = self._normalize_encoding(encoding)

        stdout, stderr = [], []

        # TODO: can we simply run this loop in the main thread now?
        # TODO: or is there some other benefit to threading it, such as
        # eventual stdin control?
        threads = self._start_threads((
            (parent_fd, out_stream, stdout, 'out' in hide, encoding),
        ))

        # Wait in main thread until child appears to have exited.
        while True:
            # TODO: set 2nd value to os.WNOHANG in some situations?
            pid_val, status = os.waitpid(pid, 0)
            # waitpid() sets the 'pid' return val to 0 when no children have
            # exited yet; when it is NOT zero, we know the child's stopped.
            if pid_val != 0:
                break
            # TODO: io sleep?

        stdout, stderr = self._obtain_outputs(threads, stdout, stderr)

        returncode = os.WEXITSTATUS(status)

        return stdout, stderr, returncode, None


class Result(object):
    """
    A container for information about the result of a command execution.

    `Result` instances have the following attributes:

    * ``stdout``: The subprocess' standard output, as a multiline string.
    * ``stderr``: Same as ``stdout`` but containing standard error (unless
      the process was invoked via a pty; see `.Runner.run`.)
    * ``exited``: An integer representing the subprocess' exit/return code.
    * ``return_code``: An alias to ``exited``.
    * ``ok``: A boolean equivalent to ``exited == 0``.
    * ``failed``: The inverse of ``ok``: ``True`` if the program exited with a
      nonzero return code.
    * ``pty``: A boolean describing whether the subprocess was invoked with a
      pty or not; see `.Runner.run`.
    * ``exception``: Typically ``None``, but may be an exception object if
      ``pty`` was ``True`` and ``run`` had to swallow an apparently-spurious
      ``OSError``. Solely for sanity checking/debugging purposes.

    `Result` objects' truth evaluation is equivalent to their ``ok``
    attribute's value.
    """
    # TODO: inherit from namedtuple instead? heh
    def __init__(self, stdout, stderr, exited, pty, exception=None):
        self.exited = self.return_code = exited
        self.stdout = stdout
        self.stderr = stderr
        self.pty = pty
        self.exception = exception

    def __nonzero__(self):
        # Holy mismatch between name and implementation, Batman!
        return self.exited == 0

    # Python 3 ahoy
    def __bool__(self):
        return self.__nonzero__()

    def __str__(self):
        ret = ["Command exited with status {0}.".format(self.exited)]
        for x in ('stdout', 'stderr'):
            val = getattr(self, x)
            ret.append("""=== {0} ===
{1}
""".format(x, val.rstrip()) if val else "(no {0})".format(x))
        return "\n".join(ret)

    @property
    def ok(self):
        return self.exited == 0

    @property
    def failed(self):
        return not self.ok
