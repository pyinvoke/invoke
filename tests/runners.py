import locale
import sys
from invoke.vendor.six import StringIO

from spec import Spec, trap, eq_, skip, ok_
from mock import patch

from invoke import Runner, Local, Context, Config

from _utils import mock_subprocess, mock_pty


class Dummy(Runner):
    def start(self, command):
        pass

    def stdout_reader(self):
        pass

    def stderr_reader(self):
        pass

    def io(self, *args):
        pass

    def wait(self):
        pass

    def returncode(self):
        return 0


def _expect_encoding(codecs, encoding):
    assert codecs.iterdecode.called
    for call in codecs.iterdecode.call_args_list:
        eq_(call[0][1], encoding)


class Runner_(Spec):
    def _run(self, *args, **kwargs):
        settings = kwargs.pop('settings', {})
        context = Context(config=Config(overrides=settings))
        return Dummy(context).run(*args, **kwargs)

    class echoing:
        @trap
        def off_by_default(self):
            self._run("my command")
            eq_(sys.stdout.getvalue(), "")

        @trap
        def enabled_via_kwarg(self):
            self._run("my command", echo=True)
            ok_("my command" in sys.stdout.getvalue())

        @trap
        def enabled_via_config(self):
            self._run("yup", settings={'run': {'echo': True}})
            ok_("yup" in sys.stdout.getvalue())

        @trap
        def kwarg_beats_config(self):
            self._run("yup", echo=True, settings={'run': {'echo': False}})
            ok_("yup" in sys.stdout.getvalue())

        @trap
        def uses_ansi_bold(self):
            self._run("my command", echo=True)
            # TODO: vendor & use a color module
            eq_(sys.stdout.getvalue(), "\x1b[1;37mmy command\x1b[0m\n")

    class encoding:
        # Use UTF-7 as a valid encoding unlikely to be a real default
        def defaults_to_encoding_method_result(self):
            runner = Dummy(Context())
            runner.encoding.return_value = 'UTF-7'
            with patch('invoke.runners.codecs') as codecs:
                runner._run("nope")
                runner.encoding.assert_called_with()
                _expect_encoding(codecs, runner.encoding.return_value)

        def honors_config(self):
            with patch('invoke.runners.codecs') as codecs:
                c = Context(Config(overrides={'run': {'encoding': 'UTF-7'}}))
                Dummy(c).run("nope")
                _expect_encoding(codecs, 'UTF-7')

        def honors_kwarg(self):
            skip()


class Local_(Spec):
    def _run(self, *args, **kwargs):
        return Local(Context()).run(*args, **kwargs)

    class stream_control:
        @trap
        @mock_subprocess(out="sup")
        def out_defaults_to_sys_stdout(self):
            "out_stream defaults to sys.stdout"
            self._run("nope")
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        @mock_subprocess(err="sup")
        def err_defaults_to_sys_stderr(self):
            "err_stream defaults to sys.stderr"
            self._run("nope")
            eq_(sys.stderr.getvalue(), "sup")

        @trap
        @mock_subprocess(out="sup")
        def out_can_be_overridden(self):
            "out_stream can be overridden"
            out = StringIO()
            self._run("nope", out_stream=out)
            eq_(out.getvalue(), "sup")
            eq_(sys.stdout.getvalue(), "")

        @trap
        @mock_subprocess(err="sup")
        def err_can_be_overridden(self):
            "err_stream can be overridden"
            err = StringIO()
            self._run("nope", err_stream=err)
            eq_(err.getvalue(), "sup")
            eq_(sys.stderr.getvalue(), "")

        @trap
        @mock_pty(out="sup")
        def pty_defaults_to_sys(self):
            self._run("nope", pty=True)
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        @mock_pty(out="yo")
        def pty_out_can_be_overridden(self):
            out = StringIO()
            self._run("nope", pty=True, out_stream=out)
            eq_(out.getvalue(), "yo")
            eq_(sys.stdout.getvalue(), "")

    class pty_fallback:
        def warning_only_fires_once(self):
            # I.e. if implementation checks pty-ness >1 time, only one warning
            # is emitted. This is kinda implementation-specific, but...
            skip()

        @mock_pty(isatty=False)
        def can_be_overridden(self):
            # Do the stuff
            self._run("nope", pty=True, fallback=False)
            # @mock_pty's asserts will be mad if pty-related os/pty calls
            # didn't fire, so we're done.

    class encoding:
        @mock_subprocess
        def uses_locale_module_for_desired_encoding(self):
            with patch('invoke.runners.codecs') as codecs:
                self._run("nope")
                local_encoding = locale.getpreferredencoding(False)
                _expect_encoding(codecs, local_encoding)
