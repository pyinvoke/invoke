# -*- coding: utf-8 -*-

import codecs
import locale
import os
import re
import struct
import sys
import threading
from functools import partial
from subprocess import Popen, PIPE

# Import some platform-specific things at top level so they can be mocked for
# tests.
try:
    import pty
except ImportError:
    pty = None
try:
    import fcntl
except ImportError:
    fcntl = None
try:
    import termios
except ImportError:
    termios = None

from .exceptions import Failure, ThreadException, ExceptionWrapper
from .platform import WINDOWS, pty_size

from .vendor import six


class Runner(object):
    """
    Partially-abstract core command-running API.

    This class is not usable by itself and must be subclassed, implementing a
    number of methods such as `start`, `wait` and `returncode`. For a subclass
    implementation example, see the source code for `.Local`.
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
        # Bookkeeping re: whether pty fallback warning has been emitted.
        self.warned_about_pty_fallback = False
        # Bookkeeping re: call/response settings
        self.responses = None

    def run(self, command, **kwargs):
        """
        Execute ``command``, returning an instance of `Result`.

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
            for its stdout/stderr streams (which defaults to the return value
            of `default_encoding`).

        :param out_stream:
            A file-like stream object to which the subprocess' standard error
            should be written. If ``None`` (the default), ``sys.stdout`` will
            be used.

        :param err_stream:
            Same as ``out_stream``, except for standard error, and defaulting
            to ``sys.stderr``.

        :param in_stream:
            A file-like stream object to used as the subprocess' standard
            input. If ``None`` (the default), ``sys.stdin`` will be used.

        :param dict responses:
            A `dict` whose keys are regular expressions to be searched for in
            the program's ``stdout`` or ``stderr``, and whose values may be any
            value one desires to write into a stdin text/binary stream
            (typically ``str`` or ``bytes`` objects depending on Python
            version) in response.

            See :doc:`/concepts/responses` for details on this functionality.

            Default: ``{}``.

        :returns:
            `Result`, or a subclass thereof.

        :raises: `.Failure` (if the command exited nonzero & ``warn=False``)

        :raises:
            `.ThreadException` (if the background I/O threads encounter
            exceptions)
        """
        # Normalize kwargs w/ config
        opts, out_stream, err_stream, in_stream = self._run_opts(kwargs)
        # Echo
        if opts['echo']:
            print("\033[1;37m{0}\033[0m".format(command))
        # Start executing the actual command (runs in background)
        self.start(command)
        # Arrive at final encoding if neither config nor kwargs had one
        self.encoding = opts['encoding'] or self.default_encoding()
        # Set up IO thread parameters
        stdout, stderr = [], []
        kwargses = [
            {
                'reader': self.stdout_reader(),
                'writer': self.stdout_writer(out_stream),
                'buffer_': stdout,
                'hide': 'out' in opts['hide'],
            },
            {
                # Notice how these are reversed from the stdout/err threads!
                'reader': self.stdin_reader(in_stream),
                'writer': self.stdin_writer(),
                # Don't buffer or respond.
                'is_output': False,
            }
        ]
        if not self.using_pty:
            kwargses.append(
                {
                    'reader': self.stderr_reader(),
                    'writer': err_stream,
                    'buffer_': stderr,
                    'hide': 'err' in opts['hide'],
                },
            )
        # Kick off IO threads
        threads, exceptions = [], []
        for kwargs in kwargses:
            t = _IOThread(target=self.io, kwargs=kwargs)
            threads.append(t)
            t.start()
        # Wait for completion, then tie things off & obtain result
        self.wait()
        for t in threads:
            t.join()
            e = t.exception()
            if e is not None:
                exceptions.append(e)
        # If any exceptions appeared inside the threads, raise them now as an
        # aggregate exception object.
        if exceptions:
            raise ThreadException(exceptions)
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
        # Get return/exit code
        exited = self.returncode()
        # Return, or raise as failure, our final result
        result = self.generate_result(
            command=command,
            stdout=stdout,
            stderr=stderr,
            exited=exited,
            pty=self.using_pty,
        )
        if not (result or opts['warn']):
            raise Failure(result)
        return result

    def _run_opts(self, kwargs):
        """
        Unify `run` kwargs with config options to arrive at local options.

        :returns:
            Four-tuple of ``(opts_dict, stdout_stream, stderr_stream,
            stdin_stream)``.
        """
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
        in_stream = opts['in_stream']
        if in_stream is None:
            in_stream = sys.stdin
        # Determine pty or no
        self.using_pty = self.should_use_pty(opts['pty'], opts['fallback'])
        # Responses
        self.responses = opts.get('responses', {})
        return opts, out_stream, err_stream, in_stream

    def generate_result(self, **kwargs):
        """
        Create & return a suitable `Result` instance from the given ``kwargs``.

        Subclasses may wish to override this in order to manipulate things or
        generate a `Result` subclass (e.g. ones containing additional metadata
        besides the default).
        """
        return Result(**kwargs)

    def io(
        self,
        reader=None,
        writer=None,
        is_output=True,
        buffer_=None,
        hide=None,
    ):
        """
        Perform I/O (reading, capturing & writing) as the body of 1+ threads.

        At the very least, each call will copy data between two streams:

        * Read bytes from a stream using the ``reader``function , giving it an
          integer number of bytes to read.
        * Decode the bytes into a string according to ``self.encoding``
          (typically derived from `default_encoding` or runtime keyword args).
        * If ``hide`` is ``False``, write those bytes using the ``writer``
          function, which takes a ``str``/``bytes`` object and should write to
          (and flush, if necessary) a stream.

        If ``is_output`` is ``True`` (the default), `io` will also treat the
        output of ``reader`` as process output, storing it & scanning for
        response playback triggers:

        * Append a copy of the bytes to ``buffer_``, typically a `list`, which
          the calling thread will expect to be mutated.
        * Run ``buffer_`` through `respond` so it has the opportunity to write
          responses to the command's stdin (see `respond` for details).
        """
        # Inner generator yielding read data
        def get():
            while True:
                data = reader(1000)
                if not data:
                    break
                # Sometimes os.read gives us bytes under Python 3...and
                # sometimes it doesn't. ¯\_(ツ)_/¯
                if not isinstance(data, six.binary_type):
                    # Can't use six.b because that just assumes latin-1 :(
                    data = data.encode(self.encoding)
                yield data
        # Decode stream using our generator & requested encoding
        for data in codecs.iterdecode(get(), self.encoding, errors='replace'):
            if not hide:
                writer(data)
            if is_output:
                buffer_.append(data)
                self.respond(buffer_)

    def respond(self, buffer_):
        """
        Write to the program's ``stdin`` in response to ``buffer_`` patterns.

        ``stdin`` is defined as "the stream returned by `get_stdin`", which
        will vary by implementation.

        The patterns and responses are driven by the key/value pairs in the
        ``responses`` kwarg of `run` - see its documentation for format
        details, and :doc:`/concepts/responses` for a conceptual overview.
        """
        # Join buffer contents into a single string; without this, we can't be
        # sure that the pattern we seek isn't split up across chunks in the
        # buffer.
        # NOTE: using string.join should be "efficient enough" for now, re:
        # speed and memory use. Should that turn up false, consider using
        # StringIO or cStringIO (tho the latter doesn't do Unicode well?)
        # which is apparently even more efficient.
        # NOTE: alternately, examine whether only preserving a (still join'd)
        # tail of the overall buffer would help - would probably help w/ memory
        # at expense of performing more operations per cycle?
        stream = u''.join(buffer_)
        for pattern, response in six.iteritems(self.responses):
            if re.search(pattern, stream):
                self.get_stdin().write(response)

    def should_use_pty(self, pty, fallback):
        """
        Should execution attempt to use a pseudo-terminal?

        :param bool pty:
            Whether the user explicitly asked for a pty.
        :param bool fallback:
            Whether falling back to non-pty execution should be allowed, in
            situations where ``pty=True`` but a pty could not be allocated.
        """
        # NOTE: fallback not used: no falling back implemented by default.
        return pty

    def default_writer(self, stream):
        """
        Return a generic local-stream-writing function closing over ``stream``.

        `default_writer` is effectively private and should never be called
        directly. By default, `stdout_writer` and `stderr_writer` pass through
        to `default_writer`, but the former are still the public interface -
        this gives subclasses the option of altering their implementation.
        """
        def writer(data):
            stream.write(data)
            stream.flush()
        return writer

    def stdout_writer(self, stream):
        """
        Return a function suitable for writing data to a stdout ``stream``.
        """
        return self.default_writer(stream)

    def stderr_writer(self, stream):
        """
        Return a function suitable for writing data to a stderr ``stream``.
        """
        return self.default_writer(stream)

    def stdin_reader(self, stream):
        """
        Return a function suitable for reading data from a stdin ``stream``.
        """
        def reader(count):
            return stream.read(count)
        return reader

    def start(self, command):
        """
        Initiate execution of ``command`` in the background.

        Typically this means use of a forked subprocess or requesting start of
        execution on a remote system.

        In most cases, this method will also set subclass-specific member
        variables used in other methods such as `wait` and/or `returncode`.
        """
        raise NotImplementedError

    def stdout_reader(self):
        """
        Return a function suitable for reading from a running command's stdout.
        """
        raise NotImplementedError

    def stderr_reader(self):
        """
        Return a function suitable for reading from a running command's stderr.
        """
        raise NotImplementedError

    def stdin_writer(self):
        """
        Return a function suitable for writing to a running command's stdin.
        """
        raise NotImplementedError

    def default_encoding(self):
        """
        Return a string naming the expected encoding of subprocess streams.

        This return value should be suitable for use by methods such as
        `codecs.iterdecode`.
        """
        raise NotImplementedError

    def wait(self):
        """
        Block until the running command appears to have exited.
        """
        raise NotImplementedError

    def returncode(self):
        """
        Return the numeric return/exit code resulting from command execution.
        """
        raise NotImplementedError


class Local(Runner):
    """
    Execute a command on the local system in a subprocess.

    .. note::
        When Invoke itself is executed without a valid PTY (i.e.
        ``os.isatty(sys.stdin)`` is ``False``), it's not possible to present a
        handle on our PTY to local subprocesses. In such situations, `Local`
        will fallback to behaving as if ``pty=False`` (on the theory that
        degraded execution is better than none at all) as well as printing a
        warning to stderr.

        To disable this behavior (i.e. if `os.isatty` is causing false
        negatives in your environment), say ``fallback=False``.
    """
    def should_use_pty(self, pty=False, fallback=True):
        use_pty = False
        if pty:
            use_pty = True
            seems_pty = (
                hasattr(sys.stdin, 'fileno')
                and callable(sys.stdin.fileno)
                and os.isatty(sys.stdin.fileno())
            )
            if not seems_pty and fallback:
                if not self.warned_about_pty_fallback:
                    sys.stderr.write("WARNING: stdin is not a pty; falling back to non-pty execution!\n") # noqa
                    self.warned_about_pty_fallback = True
                use_pty = False
        return use_pty

    def stdout_reader(self):
        if self.using_pty:
            # Need to handle spurious OSErrors on some Linux platforms.
            def reader(num_bytes):
                try:
                    return os.read(self.parent_fd, num_bytes)
                except OSError as e:
                    # Only eat this specific OSError so we don't hide others
                    if "Input/output error" not in str(e):
                        raise
                    # The bad OSErrors happen after all expected output has
                    # appeared, so we return a falsey value, which triggers the
                    # "end of output" logic in code using reader functions.
                    return None
            return reader
        else:
            return partial(os.read, self.process.stdout.fileno())

    def stderr_reader(self):
        # NOTE: when using a pty, this will never be used.
        # TODO: do we ever get those OSErrors on stderr? Feels like we could?
        return partial(os.read, self.process.stderr.fileno())

    def stdin_writer(self):
        # NOTE: parent_fd from os.fork() is a read/write pipe attached to our
        # forked process' stdout/stdin, respectively.
        fd = self.parent_fd if self.using_pty else self.process.stdin.fileno()
        return partial(os.write, fd)

    def start(self, command):
        if self.using_pty:
            if pty is None: # Encountered ImportError
                sys.exit("You indicated pty=True, but your platform doesn't support the 'pty' module!") # noqa
            cols, rows = pty_size()
            self.pid, self.parent_fd = pty.fork()
            # If we're the child process, load up the actual command in a
            # shell, just as subprocess does; this replaces our process - whose
            # pipes are all hooked up to the PTY - with the "real" one.
            if self.pid == 0:
                # TODO: both pty.spawn() and pexpect.spawn() do a lot of
                # setup/teardown involving tty.setraw, getrlimit, signal.
                # Ostensibly we'll want some of that eventually, but if
                # possible write tests - integration-level if necessary -
                # before adding it!
                #
                # Set pty window size based on what our own controlling
                # terminal's window size appears to be.
                # TODO: make subroutine?
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(sys.stdout.fileno(), termios.TIOCSWINSZ, winsize)
                # Use execv for bare-minimum "exec w/ variable # args"
                # behavior. No need for the 'p' (use PATH to find executable)
                # or 'e' (define a custom/overridden shell env) variants, for
                # now.
                # TODO: use /bin/sh or whatever subprocess does. Only using
                # bash for now because that's what we have been testing
                # against.
                # TODO: also see if subprocess is using equivalent of execvp...
                os.execv('/bin/bash', ['/bin/bash', '-c', command])
        else:
            self.process = Popen(
                command,
                shell=True,
                stdout=PIPE,
                stderr=PIPE,
                stdin=PIPE,
            )

    def default_encoding(self):
        return locale.getpreferredencoding(False)

    def wait(self):
        if self.using_pty:
            while True:
                # TODO: possibly reinstate conditional WNOHANG as per
                # https://github.com/pexpect/ptyprocess/blob/4058faa05e2940662ab6da1330aa0586c6f9cd9c/ptyprocess/ptyprocess.py#L680-L687
                pid_val, self.status = os.waitpid(self.pid, 0)
                # waitpid() sets the 'pid' return val to 0 when no children
                # have exited yet; when it is NOT zero, we know the child's
                # stopped.
                if pid_val != 0:
                    break
                # TODO: io sleep?
        else:
            self.process.wait()

    def returncode(self):
        if self.using_pty:
            return os.WEXITSTATUS(self.status)
        else:
            return self.process.returncode


class Result(object):
    """
    A container for information about the result of a command execution.

    See individual attribute/method documentation below for details.

    .. note::
        `Result` objects' truth evaluation is equivalent to their `.ok`
        attribute's value. Therefore, quick-and-dirty expressions like the
        following are possible::

            if run("some shell command"):
                do_something()
            else:
                handle_problem()
    """
    # TODO: inherit from namedtuple instead? heh
    def __init__(self, command, stdout, stderr, exited, pty):
        #: The command which was executed.
        self.command = command
        #: An integer representing the subprocess' exit/return code.
        self.exited = exited
        #: An alias for `.exited`.
        self.return_code = exited
        #: The subprocess' standard output, as a multiline string.
        self.stdout = stdout
        #: Same as `.stdout` but containing standard error (unless the process
        #: was invoked via a pty; see `.Runner.run`.)
        self.stderr = stderr
        #: A boolean describing whether the subprocess was invoked with a pty
        #: or not; see `.Runner.run`.
        self.pty = pty

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
        """
        A boolean equivalent to ``exited == 0``.
        """
        return self.exited == 0

    @property
    def failed(self):
        """
        The inverse of ``ok``.

        I.e., ``True`` if the program exited with a nonzero return code, and
        ``False`` otherwise.
        """
        return not self.ok


class _IOThread(threading.Thread):
    """
    IO thread handler making it easier for parent to handle thread exceptions.

    Based in part Fabric 1's ThreadHandler. See also Fabric GH issue #204.
    """
    def __init__(self, **kwargs):
        super(_IOThread, self).__init__(**kwargs)
        # No record of why, but Fabric used daemon threads ever since the
        # switch from select.select, so let's keep doing that.
        self.daemon = True
        # Track exceptions raised in run()
        self.kwargs = kwargs
        self.exc_info = None

    def run(self):
        try:
            super(_IOThread, self).run()
        except BaseException:
            self.exc_info = sys.exc_info()

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


def isatty(stream):
    """
    Check if a stream is a tty.

    Not all file-like objects implement the `isatty` method.
    """
    # TODO: fallback to checking os.isatty(stream)? is that ever true when a
    # stream lacks .isatty? (alt platforms? etc?)
    fn = getattr(stream, 'isatty', None)
    if fn is None:
        return False
    return fn()


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
