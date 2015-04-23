import sys
from invoke.vendor.six import StringIO

from spec import Spec, trap, eq_, skip

from invoke import Local, Context

from _utils import mock_subprocess, mock_pty


class Local_(Spec):
    def _run(self, *args, **kwargs):
        return Local(Context()).run(*args, **kwargs)

    @trap
    @mock_subprocess(out="sup")
    def out_stream_defaults_to_sys_stdout(self):
        "out_stream defaults to sys.stdout"
        self._run("nope")
        eq_(sys.stdout.getvalue(), "sup")

    @trap
    @mock_subprocess(err="sup")
    def err_stream_defaults_to_sys_stderr(self):
        "err_stream defaults to sys.stderr"
        self._run("nope")
        eq_(sys.stderr.getvalue(), "sup")

    @trap
    @mock_subprocess(out="sup")
    def out_stream_can_be_overridden(self):
        "out_stream can be overridden"
        out = StringIO()
        self._run("nope", out_stream=out)
        eq_(out.getvalue(), "sup")
        eq_(sys.stdout.getvalue(), "")

    @trap
    @mock_subprocess(err="sup")
    def err_stream_can_be_overridden(self):
        "err_stream can be overridden"
        err = StringIO()
        self._run("nope", err_stream=err)
        eq_(err.getvalue(), "sup")
        eq_(sys.stderr.getvalue(), "")

    @trap
    @mock_pty(out="sup")
    def pty_output_stream_defaults_to_sys(self):
        self._run("nope", pty=True)
        eq_(sys.stdout.getvalue(), "sup")

    @trap
    @mock_pty(out="yo")
    def pty_output_stream_overrides_work(self):
        out = StringIO()
        self._run("nope", pty=True, out_stream=out)
        eq_(out.getvalue(), "yo")
        eq_(sys.stdout.getvalue(), "")

    def pty_fallback_warnings_only_fire_once(self):
        # I.e. if implementation checks pty-ness >1 time, only one warning
        # is emitted. This is kinda implementation-specific, but...
        skip()

    def encoding_defaults_to_local_encoding(self):
        skip()

    def encoding_can_be_overridden(self):
        skip()

    @mock_pty(isatty=False)
    def fallback_can_be_overridden(self):
        # Do the stuff
        self._run("true", pty=True, fallback=False)
        # @mock_pty's asserts will be mad if pty-related os/pty calls
        # didn't fire, so we're done.
