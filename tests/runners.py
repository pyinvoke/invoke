import sys
from StringIO import StringIO

from spec import Spec, trap, eq_, skip

from invoke import Local, Context

from _utils import mock_subprocess


class Local_(Spec):
    class run:
        @trap
        @mock_subprocess(out="sup")
        def out_stream_defaults_to_sys_stdout(self):
            "out_stream defaults to sys.stdout"
            Local(Context()).run("nope")
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        @mock_subprocess(err="sup")
        def err_stream_defaults_to_sys_stderr(self):
            "err_stream defaults to sys.stderr"
            Local(Context()).run("nope")
            eq_(sys.stderr.getvalue(), "sup")

        @trap
        @mock_subprocess(out="sup")
        def out_stream_can_be_overridden(self):
            "out_stream can be overridden"
            out = StringIO()
            Local(Context()).run("nope", out_stream=out)
            eq_(out.getvalue(), "sup")
            eq_(sys.stdout.getvalue(), "")

        @trap
        @mock_subprocess(err="sup")
        def err_stream_can_be_overridden(self):
            "err_stream can be overridden"
            err = StringIO()
            Local(Context()).run("nope", err_stream=err)
            eq_(err.getvalue(), "sup")
            eq_(sys.stderr.getvalue(), "")

        def pty_output_stream_defaults_are_the_same(self):
            skip()

        def pty_output_stream_overrides_are_the_same(self):
            skip()
