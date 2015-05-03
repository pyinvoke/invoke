import os
from subprocess import Popen, PIPE
import sys
import threading
import codecs
import locale

from .exceptions import Failure, PlatformError
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
    sometimes useful.

    ``run_direct`` and ``run_pty`` are fully abstract in `Runner`; in
    subclasses, they should perform actual command execution, hooking directly
    into a subprocess' stdout/stderr pipes and returning those pipes' eventual
    full contents as distinct strings.

    ``run_direct``/``run_pty`` both have a signature of ``(self, command, warn,
    hide, encoding)`` (see `run` for semantics of these) and must return a
    4-tuple of ``(stdout, stderr, exitcode, exception)`` (see `Result` for
    their meaning).

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
        #: Context this `.Runner` operates against, referenced for
        #: configuration options (e.g. echo, warn) and possibly more,
        #: depending on subclass needs.
        self.context = context

    def run(self, command, **kwargs):
        """
        Execute ``command``, returning a `Result` object.

        .. note::
            All kwargs will default to the values found in this instance's
            `~.Runner.context` attribute, specifically in its configuration's
            ``run`` subtree. The base default values are described in the
            parameter list below.

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
                when ``pty=True``. As such, all output will appear on your
                local stdout and be captured into the ``stdout`` result
                attribute. Stderr and ``stderr`` will always be empty when
                ``pty=True``.

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
        # Do the things
        if opts['echo']:
            print("\033[1;37m{0}\033[0m".format(command))
        func = self.select_method(pty=opts['pty'], fallback=opts['fallback'])
        stdout, stderr, exited, exception = func(
            command=command,
            warn=opts['warn'],
            hide=opts['hide'],
            encoding=opts['encoding'],
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

    def run_direct(self, command, warn, hide, encoding):
        raise NotImplementedError

    def run_pty(self, command, warn, hide, encoding):
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

    def run_direct(self, command, warn, hide, encoding):
        process = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
        )

        if encoding is None:
            encoding = locale.getpreferredencoding(False)

        def display(src, dst, cap, hide):
            def get():
                while True:
                    data = os.read(src.fileno(), 1000)
                    if not data:
                        break
                    yield data
            for data in codecs.iterdecode(get(), encoding, errors='replace'):
                if not hide:
                    # Make sure no UnicodeError happens, even if the data is
                    # garbled (e.g. due to encoding mismatch with the child).
                    encoded_data = data.encode(dst.encoding, errors='replace')
                    clean_data = encoded_data.decode(dst.encoding)
                    dst.write(clean_data)
                    dst.flush()
                cap.append(data)

        stdout = []
        stderr = []
        threads = []

        for args in (
            (process.stdout, sys.stdout, stdout, 'out' in hide),
            (process.stderr, sys.stderr, stderr, 'err' in hide),
        ):
            t = threading.Thread(target=display, args=args)
            threads.append(t)
            t.start()

        process.wait()
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

        return stdout, stderr, process.returncode, None

    def run_pty(self, command, warn, hide, encoding):
        # Sanity check: platforms that can't pexpect should explode usefully
        # here. (Without this, the pexpect import throws an inner
        # ImportException trying to 'import pty' which is unavailable on
        # Windows. Better to do this here than truly-fork pexpect.)
        if WINDOWS:
            err = "You seem to be on Windows, which doesn't support ptys!"
            raise PlatformError(err)
        # Proceed as normal for POSIX/etc platforms, with a runtime import
        from .vendor import pexpect

        out = []
        def out_filter(text):
            # Maybe use encoding here as in run() above...
            out.append(text.decode("utf-8", 'replace'))
            if 'out' not in hide:
                return text
            else:
                return b""
        p = pexpect.spawn("/bin/bash", ["-c", command])
        # Ensure pexpect doesn't barf with OSError if we fall off the end of
        # the child's input on some platforms (e.g. Linux).
        exception = None
        try:
            p.interact(output_filter=out_filter)
        except OSError as e:
            # Only capture the OSError we expect
            if "Input/output error" not in str(e):
                raise
            # Ensure it ties off the child, sets exitstatus, etc
            p.close()
            # Capture the exception in case it's NOT the OSError we think it
            # is and folks need to debug
            exception = e
        return "".join(out), "", p.exitstatus, exception


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
