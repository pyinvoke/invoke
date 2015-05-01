import locale
import sys
from invoke.vendor.six import StringIO

from spec import Spec, trap, eq_, skip, ok_, raises
from mock import patch, Mock

from invoke import Runner, Local, Context, Config, Failure

from _utils import mock_subprocess, mock_pty


class Dummy(Runner):
    """
    Dummy runner subclass that does minimum work required to execute run().
    """
    def start(self, command):
        pass

    def stdout_reader(self):
        return lambda n: ""

    def stderr_reader(self):
        return lambda n: ""

    def default_encoding(self):
        return "US-ASCII"

    def wait(self):
        pass

    def returncode(self):
        return 0


def _expect_encoding(codecs, encoding):
    assert codecs.iterdecode.called
    for call in codecs.iterdecode.call_args_list:
        eq_(call[0][1], encoding)

def _run(*args, **kwargs):
    klass = kwargs.pop('klass', Dummy)
    settings = kwargs.pop('settings', {})
    context = Context(config=Config(overrides=settings))
    return klass(context).run(*args, **kwargs)

def _runner(out='', err='', **kwargs):
    klass = kwargs.pop('klass', Dummy)
    runner = klass(Context(config=Config(overrides=kwargs)))
    if 'exits' in kwargs:
        runner.returncode = Mock(return_value=kwargs.pop('exits'))
    out_file = StringIO(out)
    err_file = StringIO(err)
    def out_reader(count):
        return out_file.read(count)
    def err_reader(count):
        return err_file.read(count)
    runner.stdout_reader = lambda: out_reader
    runner.stderr_reader = lambda: err_reader
    return runner


class Runner_(Spec):
    def _run(self, *args, **kwargs):
        return _run(*args, **kwargs)

    def _runner(self, *args, **kwargs):
        return _runner(*args, **kwargs)

    class init:
        "__init__"
        def takes_a_context_instance(self):
            c = Context()
            eq_(Runner(c).context, c)

        @raises(TypeError)
        def context_instance_is_required(self):
            Runner()

    class warn:
        def honors_config(self):
            runner = self._runner(run={'warn': True}, exits=1)
            # Doesn't raise Failure -> all good
            runner.run("nope")

        def kwarg_beats_config(self):
            runner = self._runner(run={'warn': False}, exits=1)
            # Doesn't raise Failure -> all good
            runner.run("nope", warn=True)

    class hide:
        @trap
        def honors_config(self):
            runner = self._runner(out='stuff', run={'hide': True})
            r = runner.run("nope")
            eq_(r.stdout, 'stuff')
            eq_(sys.stdout.getvalue(), '')

        @trap
        def kwarg_beats_config(self):
            runner = self._runner(out='stuff')
            r = runner.run("nope", hide=True)
            eq_(r.stdout, 'stuff')
            eq_(sys.stdout.getvalue(), '')

    class pty:
        def pty_defaults_to_off(self):
            eq_(self._run("nope").pty, False)

        def honors_config(self):
            runner = self._runner(run={'pty': True})
            eq_(runner.run("nope").pty, True)

        def kwarg_beats_config(self):
            runner = self._runner(run={'pty': False})
            eq_(runner.run("nope", pty=True).pty, True)

    class return_value:
        def return_code_in_result(self):
            """
            Result has .return_code (and .exited) containing exit code int
            """
            runner = self._runner(exits=17)
            r = runner.run("nope", warn=True)
            eq_(r.return_code, 17)
            eq_(r.exited, 17)

        def ok_attr_indicates_success(self):
            runner = self._runner()
            eq_(runner.run("nope").ok, True) # default dummy retval is 0

        def ok_attr_indicates_failure(self):
            runner = self._runner(exits=1)
            eq_(runner.run("nope", warn=True).ok, False)

        def failed_attr_indicates_success(self):
            runner = self._runner()
            eq_(runner.run("nope").failed, False) # default dummy retval is 0

        def failed_attr_indicates_failure(self):
            runner = self._runner(exits=1)
            eq_(runner.run("nope", warn=True).failed, True)

        @trap
        def stdout_attribute_contains_stdout(self):
            runner = self._runner(out='foo')
            eq_(runner.run("nope").stdout, "foo")
            eq_(sys.stdout.getvalue(), "foo")

        @trap
        def stderr_attribute_contains_stderr(self):
            runner = self._runner(err='foo')
            eq_(runner.run("nope").stderr, "foo")
            eq_(sys.stderr.getvalue(), "foo")

        def whether_pty_was_used(self):
            eq_(self._run("nope").pty, False)
            eq_(self._run("nope", pty=True).pty, True)

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
            runner = self._runner()
            encoding = 'UTF-7'
            runner.default_encoding = Mock(return_value=encoding)
            with patch('invoke.runners.codecs') as codecs:
                runner.run("nope")
                runner.default_encoding.assert_called_with()
                _expect_encoding(codecs, encoding)

        def honors_config(self):
            with patch('invoke.runners.codecs') as codecs:
                c = Context(Config(overrides={'run': {'encoding': 'UTF-7'}}))
                Dummy(c).run("nope")
                _expect_encoding(codecs, 'UTF-7')

        def honors_kwarg(self):
            skip()

    class stream_control:
        @trap
        def out_defaults_to_sys_stdout(self):
            "out_stream defaults to sys.stdout"
            self._runner(out="sup").run("nope")
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        def err_defaults_to_sys_stderr(self):
            "err_stream defaults to sys.stderr"
            self._runner(err="sup").run("nope")
            eq_(sys.stderr.getvalue(), "sup")

        @trap
        def out_can_be_overridden(self):
            "out_stream can be overridden"
            out = StringIO()
            self._runner(out="sup").run("nope", out_stream=out)
            eq_(out.getvalue(), "sup")
            eq_(sys.stdout.getvalue(), "")

        @trap
        def err_can_be_overridden(self):
            "err_stream can be overridden"
            err = StringIO()
            self._runner(err="sup").run("nope", err_stream=err)
            eq_(err.getvalue(), "sup")
            eq_(sys.stderr.getvalue(), "")

        @trap
        def pty_defaults_to_sys(self):
            self._runner(out="sup").run("nope", pty=True)
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        def pty_out_can_be_overridden(self):
            out = StringIO()
            self._runner(out="yo").run("nope", pty=True, out_stream=out)
            eq_(out.getvalue(), "yo")
            eq_(sys.stdout.getvalue(), "")


    class failure_handling:
        @raises(Failure)
        def fast_failures(self):
            self._runner(exits=1).run("nope")

        def non_one_return_codes_still_act_as_failure(self):
            r = self._runner(exits=17).run("nope", warn=True)
            eq_(r.failed, True)

        def Failure_repr_includes_stderr(self):
            try:
                self._runner(exits=1, err="ohnoz").run("nope", hide=True)
                assert false # noqa. Ensure failure to Failure fails
            except Failure as f:
                r = repr(f)
                err = "Sentinel 'ohnoz' not found in {0!r}".format(r)
                assert 'ohnoz' in r, err

class Local_(Spec):
    def _run(self, *args, **kwargs):
        return _run(*args, **dict(kwargs, klass=Local))

    def _runner(self, *args, **kwargs):
        return _runner(*args, **dict(kwargs, klass=Local))

    class pty_fallback:
        def warning_only_fires_once(self):
            # I.e. if implementation checks pty-ness >1 time, only one warning
            # is emitted. This is kinda implementation-specific, but...
            skip()

        @mock_pty(isatty=False)
        def can_be_overridden_by_kwarg(self):
            self._run("nope", pty=True, fallback=False)
            # @mock_pty's asserts will be mad if pty-related os/pty calls
            # didn't fire, so we're done.

        @mock_pty(isatty=False)
        def can_be_overridden_by_config(self):
            self._runner(run={'fallback': False}).run("nope", pty=True)
            # @mock_pty's asserts will be mad if pty-related os/pty calls
            # didn't fire, so we're done.

        @trap
        @mock_subprocess(isatty=False)
        def fallback_affects_result_pty_value(self, *mocks):
            eq_(self._run("nope", pty=True).pty, False)

        @mock_pty(isatty=False)
        def overridden_fallback_affects_result_pty_value(self):
            eq_(self._run("nope", pty=True, fallback=False).pty, True)

    class encoding:
        @mock_subprocess
        def uses_locale_module_for_desired_encoding(self):
            with patch('invoke.runners.codecs') as codecs:
                self._run("nope")
                local_encoding = locale.getpreferredencoding(False)
                _expect_encoding(codecs, local_encoding)
