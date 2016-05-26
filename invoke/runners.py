# -*- coding: utf-8 -*-

import codecs
import locale
import os
import re
from signal import SIGINT, SIGTERM
import struct
from subprocess import Popen, PIPE
import sys
import threading
import time

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

from .exceptions import Failure, ThreadException
from .platform import (
    WINDOWS, pty_size, character_buffered, ready_for_reading, read_byte,
)
from .util import has_fileno, isatty, ExceptionHandlingThread

from .vendor import six


class Runner(object):
    """
    Partially-abstract core command-running API.

    This class is not usable by itself and must be subclassed, implementing a
    number of methods such as `start`, `wait` and `returncode`. For a subclass
    implementation example, see the source code for `.Local`.
    """
    read_chunk_size = 1000
    input_sleep = 0.01

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
        #: A `threading.Event` signaling program completion.
        #:
        #: Typically set after `wait` returns. Some IO mechanisms rely on this
        #: to know when to exit an infinite read loop.
        self.program_finished = threading.Event()
        # I wish Sphinx would organize all class/instance attrs in the same
        # place. If I don't do this here, it goes 'class vars -> __init__
        # docstring -> instance vars' :( TODO: consider just merging class and
        # __init__ docstrings, though that's annoying too.
        #: How many bytes (at maximum) to read per iteration of stream reads.
        self.read_chunk_size = self.__class__.read_chunk_size
        # Ditto re: declaring this in 2 places for doc reasons.
        #: How many seconds to sleep on each iteration of the stdin read loop.
        self.input_sleep = self.__class__.input_sleep
        #: Whether pty fallback warning has been emitted.
        self.warned_about_pty_fallback = False
        #: The trigger/response mapping for use by `respond`. Is filled in at
        #: runtime by `run`.
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

        :param str shell: Which shell binary to use. Default: ``/bin/bash``.

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

            .. note::
                ``hide=True`` will also override ``echo=True`` if both are
                given (either as kwargs or via config/CLI).

        :param bool pty:
            By default, ``run`` connects directly to the invoked process and
            reads its stdout/stderr streams. Some programs will buffer (or even
            behave) differently in this situation compared to using an actual
            terminal or pseudoterminal (pty). To use a pty instead of the
            default behavior, specify ``pty=True``.

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

            .. note::
                ``hide=True`` will override ``echo=True`` if both are given.

        :param dict env:
            By default, subprocesses recieve a copy of Invoke's own environment
            (i.e. ``os.environ``). Supply a dict here to update that child
            environment.

            For example, ``run('command', env={'PYTHONPATH':
            '/some/virtual/env/maybe'})`` would modify the ``PYTHONPATH`` env
            var, with the rest of the child's env looking identical to the
            parent.

            .. seealso:: ``replace_env`` for changing 'update' to 'replace'.

        :param bool replace_env:
            When ``True``, causes the subprocess to receive the dictionary
            given to ``env`` as its entire shell environment, instead of
            updating a copy of ``os.environ`` (which is the default behavior).
            Default: ``False``.

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

        :param bool echo_stdin:
            Whether to write data from ``in_stream`` back to ``out_stream``.

            In other words, in normal interactive usage, this parameter
            controls whether Invoke mirrors what you type back to your
            terminal.

            By default (when ``None``), this behavior is triggered by the
            following:

                * Not using a pty to run the subcommand (i.e. ``pty=False``),
                  as ptys natively echo stdin to stdout on their own;
                * And when the controlling terminal of Invoke itself (as per
                  ``in_stream``) appears to be a valid terminal device or TTY.
                  (Specifically, when `~invoke.util.isatty` yields a ``True``
                  result when given ``in_stream``.)

                  .. note::
                      This property tends to be ``False`` when piping another
                      program's output into an Invoke session, or when running
                      Invoke within another program (e.g. running Invoke from
                      itself).

            If both of those properties are true, echoing will occur; if either
            is false, no echoing will be performed.

            When not ``None``, this parameter will override that auto-detection
            and force, or disable, echoing.

        :returns:
            `Result`, or a subclass thereof.

        :raises: `.Failure`, if the command exited nonzero & ``warn=False``.

        :raises:
            `.ThreadException` (if the background I/O threads encounter
            exceptions).

        :raises:
            ``KeyboardInterrupt``, if the user generates one during command
            execution by pressing Ctrl-C.

            .. note::
                In normal usage, Invoke's top-level CLI tooling will catch
                these & exit with return code ``130`` (typical POSIX behavior)
                instead of printing a traceback and exiting ``1`` (which is
                what Python normally does).
        """
        # Normalize kwargs w/ config
        opts, out_stream, err_stream, in_stream = self._run_opts(kwargs)
        shell = opts['shell']
        # Environment setup
        env = self.generate_env(opts['env'], opts['replace_env'])
        # Echo running command
        if opts['echo']:
            print("\033[1;37m{0}\033[0m".format(command))
        # Start executing the actual command (runs in background)
        self.start(command, shell, env)
        # Arrive at final encoding if neither config nor kwargs had one
        self.encoding = opts['encoding'] or self.default_encoding()
        # Set up IO thread parameters (format - body_func: {kwargs})
        stdout, stderr = [], []
        thread_args = {
            self.handle_stdout: {
                'buffer_': stdout,
                'hide': 'out' in opts['hide'],
                'output': out_stream,
            },
            # TODO: make this & related functionality optional, for users who
            # don't care about autoresponding & are encountering issues with
            # the stdin mirroring? Downside is it fragments expected behavior &
            # puts folks with true interactive use cases in a different support
            # class.
            self.handle_stdin: {
                'input_': in_stream,
                'output': out_stream,
                'echo': opts['echo_stdin'],
            }
        }
        if not self.using_pty:
            thread_args[self.handle_stderr] = {
                'buffer_': stderr,
                'hide': 'err' in opts['hide'],
                'output': err_stream,
            }
        # Kick off IO threads
        threads, exceptions = [], []
        for target, kwargs in six.iteritems(thread_args):
            t = ExceptionHandlingThread(target=target, kwargs=kwargs)
            threads.append(t)
            t.start()
        # Wait for completion, then tie things off & obtain result
        # And make sure we perform that tying off even if things asplode.
        exception = None
        try:
            self.wait()
        except BaseException as e: # Make sure we nab ^C etc
            exception = e
            # TODO: consider consuming the KeyboardInterrupt instead of storing
            # it for later raise; this would allow for subprocesses which don't
            # actually exit on Ctrl-C (e.g. vim). NOTE: but this would make it
            # harder to correctly detect it and exit 130 once everything wraps
            # up...
            # TODO: generally, but especially if we do ignore
            # KeyboardInterrupt, honor other signals sent to our own process
            # and transmit them to the subprocess before handling 'normally'.
            # NOTE: we handle this now instead of at actual-exception-handling
            # time because otherwise the stdout/err reader threads may block
            # until the subprocess exits.
            if isinstance(exception, KeyboardInterrupt):
                self.send_interrupt()
        self.program_finished.set()
        for t in threads:
            t.join()
            e = t.exception()
            if e is not None:
                exceptions.append(e)
        # If we got a main-thread exception while wait()ing, raise it now that
        # we've closed our worker threads.
        if exception is not None:
            raise exception
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
            shell=shell,
            env=env,
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
        # If hide was True, turn off echoing
        if opts['hide'] is True:
            opts['echo'] = False
        # Then normalize 'hide' from one of the various valid input values,
        # into a stream-names tuple.
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
        # TODO: precompile the keys into regex objects
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

    def encode(self, data):
        """
        Encode ``data`` read from some I/O stream, into a useful str/bytes.
        """
        # TODO: shouldn't this decode, not encode? oh god
        # Sometimes os.read gives us bytes under Python 3...and
        # sometimes it doesn't. ¯\_(ツ)_/¯
        # TODO: this is dumb, as pfmoore has probably said before.
        if not isinstance(data, six.binary_type):
            # Can't use six.b because that just assumes latin-1 :(
            data = data.encode(self.encoding)
        return data

    def read_proc_output(self, reader):
        """
        Iteratively read & decode bytes from a subprocess' out/err stream.

        :param function reader:
            A literal reader function/partial, wrapping the actual stream
            object in question, which takes a number of bytes to read, and
            returns that many bytes (or ``None``).

            ``reader`` should be a reference to either `read_proc_stdout` or
            `read_proc_stderr`, which perform the actual, platform/library
            specific read calls.

        :returns:
            A generator yielding Unicode strings (`unicode` on Python 2; `str`
            on Python 3).

            Specifically, each resulting string is the result of encoding
            `read_chunk_size` bytes read from the subprocess' out/err stream.
        """
        # Create a generator yielding stdout data.
        # NOTE: Typically, reading from any stdout/err (local, remote or
        # otherwise) can be thought of as "read until you get nothing back".
        # This is preferable over "wait until an out-of-band signal claims the
        # process is done running" because sometimes that signal will appear
        # before we've actually read all the data in the stream (i.e.: a race
        # condition).
        def get():
            while True:
                data = reader(self.read_chunk_size)
                if not data:
                    break
                # TODO: potentially move/copy self.encode in here, depending on
                # where else it's used
                yield self.encode(data)
        # Use that generator in iterdecode so it ends up in our local encoding.
        for data in codecs.iterdecode(
            # TODO: errors= may need to change depending on discussion from
            # #274?
            get(), self.encoding, errors='replace'
        ):
            # TODO: presumably this can become 'return codecs.iterdecode(...)'?
            # TODO: I sitll dunno why we are using iterdecode exactly, nor why
            # we self.encode and then iterdecode, is this just a poorly
            # documented round-tripping?
            yield data

    def _handle_output(self, buffer_, hide, output, reader, indices):
        for data in self.read_proc_output(reader):
            # Echo to local stdout if necessary
            # TODO: should we rephrase this as "if you want to hide, give me a
            # dummy output stream, e.g. something like /dev/null"? Otherwise, a
            # combo of 'hide=stdout' + 'here is an explicit out_stream' means
            # out_stream is never written to, and that seems...odd.
            if not hide:
                output.write(data)
                output.flush()
            # Store in shared buffer so main thread can do things with the
            # result after execution completes.
            # NOTE: this is threadsafe insofar as no reading occurs until after
            # the thread is join()'d.
            buffer_.append(data)
            # Run our specific buffer & indices through the autoresponder
            self.respond(buffer_, indices)

    def handle_stdout(self, buffer_, hide, output):
        """
        Read process' stdout, storing into a buffer & printing/parsing.

        Intended for use as a thread target. Only terminates when all stdout
        from the subprocess has been read.

        :param list buffer_: The capture buffer shared with the main thread.
        :param bool hide: Whether or not to replay data into ``output``.
        :param output:
            Output stream (file-like object) to write data into when not
            hiding.

        :returns: ``None``.
        """
        self._handle_output(
            buffer_,
            hide,
            output,
            reader=self.read_proc_stdout,
            indices=threading.local(),
        )

    def handle_stderr(self, buffer_, hide, output):
        """
        Read process' stderr, storing into a buffer & printing/parsing.

        Identical to `handle_stdout` except for the stream read from; see its
        docstring for API details.
        """
        self._handle_output(
            buffer_,
            hide,
            output,
            reader=self.read_proc_stderr,
            indices=threading.local(),
        )

    def read_our_stdin(self, input_):
        """
        Read & decode one byte from a local stdin stream.

        :param input_:
            Actual stream object to read from. Maps to ``in_stream`` in `run`,
            so will often be ``sys.stdin``, but might be any stream-like
            object.

        :returns:
            A Unicode string, the result of decoding the read byte; or ``None``
            if the stream didn't appear ready for reading.
        """
        # TODO: consider moving the character_buffered contextmanager call in
        # here? Downside is it would be flipping those switches for every byte
        # read instead of once per session, which could be costly (?).
        byte = None
        if ready_for_reading(input_):
            byte = read_byte(input_)
            if byte:
                # TODO: will this break with multibyte input character
                # encoding?
                byte = self.encode(byte)
        return byte

    def handle_stdin(self, input_, output, echo):
        """
        Read local stdin, copying into process' stdin as necessary.

        Intended for use as a thread target.

        .. note::
            Because real terminal stdin streams have no well-defined "end", if
            such a stream is detected (based on existence of a callable
            ``.fileno()``) this method will wait until `program_finished` is
            set, before terminating.

            When the stream doesn't appear to be from a terminal, the same
            semantics as `handle_stdout` are used - the stream is simply
            ``read()`` from until it returns an empty value.

        :param input_: Stream (file-like object) from which to read.
        :param output: Stream (file-like object) to which echoing may occur.
        :param bool echo: User override option for stdin-stdout echoing.

        :returns: ``None``.
        """
        with character_buffered(input_):
            while True:
                # Read 1 byte at a time for interactivity's sake.
                byte = self.read_our_stdin(input_)
                if byte:
                    # Mirror what we just read to process' stdin.
                    # We perform an encode so Python 3 gets bytes (streams +
                    # str's in Python 3 == no bueno) but skip the decode step,
                    # since there's presumably no need (nobody's interacting
                    # with this data programmatically).
                    self.write_proc_stdin(byte)
                    # Also echo it back to local stdout (or whatever
                    # out_stream is set to) when necessary.
                    if echo is None:
                        echo = self.should_echo_stdin(input_, output)
                    if echo:
                        output.write(byte) # TODO: encode?
                        output.flush()
                else:
                    # When reading from file-like objects that aren't "real"
                    # terminal streams, an empty byte signals EOF.
                    break
                # Dual all-done signals: program being executed is done
                # running, *and* we don't seem to be reading anything out of
                # stdin. (If we only test the former, we may encounter race
                # conditions re: unread stdin.)
                # TODO: shouldn't the 'not byte' always end up break'ing above?
                if self.program_finished.is_set() and not byte:
                    break
                # Take a nap so we're not chewing CPU.
                time.sleep(self.input_sleep)

        # while not self.program_finished.is_set():
        #    # TODO: reinstate lock/whatever thread logic from fab v1 which
        #    # prevents reading from stdin while other parts of the code are
        #    # prompting for runtime passwords? (search for 'input_enabled')
        #    if have_char and chan.input_enabled:
        #        # Send all local stdin to remote end's stdin
        #        #byte = msvcrt.getch() if WINDOWS else sys.stdin.read(1)
        #        yield self.encode(sys.stdin.read(1))
        #        # Optionally echo locally, if needed.
        #        # TODO: how to truly do this? access the out_stream which
        #        # isn't currently visible to us? if we just skip this part,
        #        # interactive users may not have their input echoed...ISTR we
        #        # used to assume remote would send it back down stdout/err...
        #        # clearly not?
        #        #if not using_pty and env.echo_stdin:
        #            # Not using fastprint() here -- it prints as 'user'
        #            # output level, don't want it to be accidentally hidden
        #        #    sys.stdout.write(byte)
        #        #    sys.stdout.flush()

    def should_echo_stdin(self, input_, output):
        """
        Determine whether data read from ``input_`` should echo to ``output``.

        Used by `handle_stdin`; tests attributes of ``input_`` and ``output``.

        :param input_: Input stream (file-like object).
        :param output: Output stream (file-like object).
        :returns: A ``bool``.
        """
        return (not self.using_pty) and isatty(input_)

    def respond(self, buffer_, indices):
        """
        Write to the program's stdin in response to patterns in ``buffer_``.

        The patterns and responses are driven by the key/value pairs in the
        ``responses`` kwarg of `run` - see its documentation for format
        details, and :doc:`/concepts/responses` for a conceptual overview.

        :param list buffer:
            The capture buffer for this thread's particular IO stream.

        :param indices:
            A `threading.local` object upon which is (or will be) stored the
            last-seen index for each key in ``responses``. Allows the responder
            functionality to be used by multiple threads (typically, one each
            for stdout and stderr) without conflicting.

        :returns: ``None``.
        """
        # Short-circuit if there are no responses to respond to. This saves us
        # the effort of joining the buffer and so forth.
        if not self.responses:
            return
        # Join buffer contents into a single string; without this, we can't be
        # sure that the pattern we seek isn't split up across chunks in the
        # buffer.
        # NOTE: using string.join should be "efficient enough" for now, re:
        # speed and memory use. Should that turn up false, consider using
        # StringIO or cStringIO (tho the latter doesn't do Unicode well?)
        # which is apparently even more efficient.
        stream = u''.join(buffer_)
        # Initialize seek indices
        if not hasattr(indices, 'seek'):
            indices.seek = {}
            for pattern in self.responses:
                indices.seek[pattern] = 0
        for pattern, response in six.iteritems(self.responses):
            # Only look at stream contents we haven't seen yet, to avoid dupes.
            new_ = stream[indices.seek[pattern]:]
            # Search, across lines if necessary
            matches = re.findall(pattern, new_, re.S)
            # Update seek index if we've matched
            if matches:
                indices.seek[pattern] += len(new_)
            # Iterate over findall() response in case >1 match occurred.
            for match in matches:
                # TODO: automatically append system-appropriate newline if
                # response doesn't end with it, w/ option to disable?
                # NOTE: have to 'encode' response here so Python 3 gets actual
                # bytes, otherwise os.write gets its knickers atwist.
                self.write_proc_stdin(self.encode(response))

    def generate_env(self, env, replace_env):
        """
        Return a suitable environment dict based on user input & behavior.

        :param dict env: Dict supplying overrides or full env, depending.
        :param bool replace_env:
            Whether ``env`` updates, or is used in place of, the value of
            `os.environ`.

        :returns: A dictionary of shell environment vars.
        """
        return env if replace_env else dict(os.environ, **env)

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

    def start(self, command, shell, env):
        """
        Initiate execution of ``command`` (via ``shell``, with ``env``).

        Typically this means use of a forked subprocess or requesting start of
        execution on a remote system.

        In most cases, this method will also set subclass-specific member
        variables used in other methods such as `wait` and/or `returncode`.
        """
        raise NotImplementedError

    def read_proc_stdout(self, num_bytes):
        """
        Read ``num_bytes`` from the running process' stdout stream.

        :param int num_bytes: Number of bytes to read at maximum.

        :returns: A string/bytes object.
        """
        raise NotImplementedError

    def read_proc_stderr(self, num_bytes):
        """
        Read ``num_bytes`` from the running process' stderr stream.

        :param int num_bytes: Number of bytes to read at maximum.

        :returns: A string/bytes object.
        """
        raise NotImplementedError

    def write_proc_stdin(self, data):
        """
        Write ``data`` to the running process' stdin.
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

    def send_interrupt(self):
        """
        Submit an interrupt signal to the running subprocess.
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
        When Invoke itself is executed without a controlling terminal (e.g.
        when ``sys.stdin`` lacks a useful ``fileno``), it's not possible to
        present a handle on our PTY to local subprocesses. In such situations,
        `Local` will fallback to behaving as if ``pty=False`` (on the theory
        that degraded execution is better than none at all) as well as printing
        a warning to stderr.

        To disable this behavior, say ``fallback=False``.
    """
    def should_use_pty(self, pty=False, fallback=True):
        use_pty = False
        if pty:
            use_pty = True
            # TODO: pass in & test in_stream, not sys.stdin
            if not has_fileno(sys.stdin) and fallback:
                if not self.warned_about_pty_fallback:
                    sys.stderr.write("WARNING: stdin has no fileno; falling back to non-pty execution!\n") # noqa
                    self.warned_about_pty_fallback = True
                use_pty = False
        return use_pty

    def read_proc_stdout(self, num_bytes):
        # Obtain useful read-some-bytes function
        if self.using_pty:
            # Need to handle spurious OSErrors on some Linux platforms.
            try:
                data = os.read(self.parent_fd, num_bytes)
            except OSError as e:
                # Only eat this specific OSError so we don't hide others
                if "Input/output error" not in str(e):
                    raise
                # The bad OSErrors happen after all expected output has
                # appeared, so we return a falsey value, which triggers the
                # "end of output" logic in code using reader functions.
                data = None
        else:
            data = os.read(self.process.stdout.fileno(), num_bytes)
        return data

    def read_proc_stderr(self, num_bytes):
        # NOTE: when using a pty, this will never be called.
        # TODO: do we ever get those OSErrors on stderr? Feels like we could?
        return os.read(self.process.stderr.fileno(), num_bytes)

    def write_proc_stdin(self, data):
        # NOTE: parent_fd from os.fork() is a read/write pipe attached to our
        # forked process' stdout/stdin, respectively.
        fd = self.parent_fd if self.using_pty else self.process.stdin.fileno()
        # Try to write, ignoring broken pipes if encountered (implies child
        # process exited before the process piping stdin to us finished;
        # there's nothing we can do about that!)
        try:
            return os.write(fd, data)
        except OSError as e:
            if 'Broken pipe' not in str(e):
                raise

    def start(self, command, shell, env):
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
                # Use execve for bare-minimum "exec w/ variable # args + env"
                # behavior. No need for the 'p' (use PATH to find executable)
                # for now.
                # TODO: see if subprocess is using equivalent of execvp...
                os.execve(shell, [shell, '-c', command], env)
        else:
            self.process = Popen(
                command,
                shell=True,
                executable=shell,
                env=env,
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

    def send_interrupt(self):
        if self.using_pty:
            os.kill(self.pid, SIGINT)
        else:
            # Use send_signal with platform-appropriate signal (Windows doesn't
            # support SIGINT unfortunately, only SIGTERM).
            # NOTE: could use subprocess.terminate() (which is cross-platform)
            # but feels best to use SIGINT as much as we possibly can as it's
            # most appropriate. terminate() always sends SIGTERM.
            # NOTE: in interactive POSIX terminals, this is technically
            # unnecessary as Ctrl-C submits the INT to the entire foreground
            # process group (which will be both Invoke and its spawned
            # subprocess). However, it doesn't seem to hurt, & ensures that a
            # *non-interactive* SIGINT is forwarded correctly.
            self.process.send_signal(SIGINT if not WINDOWS else SIGTERM)

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
    def __init__(self, command, shell, env, stdout, stderr, exited, pty):
        #: The command which was executed.
        self.command = command
        #: The shell binary used for execution.
        self.shell = shell
        #: The shell environment used for execution.
        self.env = env
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
