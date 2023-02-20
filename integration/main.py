import os
from pathlib import Path
import sys

import pytest
from pytest_relaxed import trap

from invoke import run
from invoke._version import __version__
from invoke.terminals import WINDOWS

from ._util import only_utf8


def _output_eq(cmd: str, expected: str) -> None:
    r = run(cmd, hide=True)
    assert r is not None
    assert r.stdout == expected


class Main:
    def setup_method(self) -> None:
        self.cwd = os.getcwd()
        # Enter integration/_support as all support files are in there now
        os.chdir(Path(__file__).parent / "_support")

    def teardown_method(self) -> None:
        os.chdir(self.cwd)

    class basics:
        @trap
        def basic_invocation(self) -> None:
            _output_eq("invoke print-foo", "foo\n")

        @trap
        def version_output(self) -> None:
            _output_eq("invoke --version", "Invoke {}\n".format(__version__))

        @trap
        def help_output(self) -> None:
            r = run("invoke --help")
            assert r is not None
            assert "Usage: inv[oke] " in r.stdout

        @trap
        def per_task_help(self) -> None:
            r = run("invoke -c _explicit foo --help")
            assert r is not None
            assert "Frobazz" in r.stdout

        @trap
        def shorthand_binary_name(self) -> None:
            _output_eq("inv print-foo", "foo\n")

        @trap
        def explicit_task_module(self) -> None:
            _output_eq("inv --collection _explicit foo", "Yup\n")

        @trap
        def invocation_with_args(self) -> None:
            _output_eq("inv print-name --name whatevs", "whatevs\n")

        @trap
        def bad_collection_exits_nonzero(self) -> None:
            result = run("inv -c nope -l", warn=True)
            assert result is not None
            assert result.exited == 1
            assert not result.stdout
            assert result.stderr

        def loads_real_user_config(self) -> None:
            path = os.path.expanduser("~/.invoke.yaml")
            try:
                with open(path, "w") as fd:
                    fd.write("foo: bar")
                _output_eq("inv print-config", "bar\n")
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass

        @trap
        def invocable_via_python_dash_m(self) -> None:
            _output_eq(
                "python -m invoke print-name --name mainline", "mainline\n"
            )

    class funky_characters_in_stdout:
        @only_utf8
        def basic_nonstandard_characters(self) -> None:
            # Crummy "doesn't explode with decode errors" test
            cmd = ("type" if WINDOWS else "cat") + " tree.out"
            run(cmd, hide="stderr")

        @only_utf8
        def nonprinting_bytes(self) -> None:
            # Seriously non-printing characters (i.e. non UTF8) also don't
            # asplode (they would print as escapes normally, but still)
            run("echo '\xff'", hide="stderr")

        @only_utf8
        def nonprinting_bytes_pty(self) -> None:
            if WINDOWS:
                return
            # PTY use adds another utf-8 decode spot which can also fail.
            run("echo '\xff'", pty=True, hide="stderr")

    class ptys:
        def complex_nesting_under_ptys_doesnt_break(self) -> None:
            if WINDOWS:  # Not sure how to make this work on Windows
                return
            # GH issue 191
            substr = "      hello\t\t\nworld with spaces"
            cmd = """ eval 'echo "{}" ' """.format(substr)
            expected = "      hello\t\t\r\nworld with spaces\r\n"
            r = run(cmd, pty=True, hide="both")
            assert r is not None
            assert r.stdout == expected

        def pty_puts_both_streams_in_stdout(self) -> None:
            if WINDOWS:
                return
            err_echo = "{} err.py".format(sys.executable)
            command = "echo foo && {} bar".format(err_echo)
            r = run(command, hide="both", pty=True)
            assert r is not None
            assert r.stdout == "foo\r\nbar\r\n"
            assert r.stderr == ""

        def simple_command_with_pty(self) -> None:
            """
            Run command under PTY
            """
            # Most Unix systems should have stty, which asplodes when not run
            # under a pty, and prints useful info otherwise
            result = run("stty -a", hide=True, pty=True)
            # PTYs use \r\n, not \n, line separation
            assert result is not None
            assert "\r\n" in result.stdout
            assert result.pty is True

        @pytest.mark.skip(reason="CircleCI env actually does have 0x0 stty")
        def pty_size_is_realistic(self) -> None:
            # When we don't explicitly set pty size, 'stty size' sees it as
            # 0x0.
            # When we do set it, it should be some non 0x0, non 80x24 (the
            # default) value. (yes, this means it fails if you really do have
            # an 80x24 terminal. but who does that?)
            r = run("stty size", hide=True, pty=True)
            assert r is not None
            size = r.stdout.strip()
            assert size != ""
            assert size != "0 0"
            assert size != "24 80"

    class parsing:
        def false_as_optional_arg_default_value_works_okay(self) -> None:
            # (Dis)proves #416. When bug present, parser gets very confused,
            # asks "what the hell is 'whee'?". See also a unit test for
            # Task.get_arguments.
            for argstr, expected in (
                ("", "False"),
                ("--meh", "True"),
                ("--meh=whee", "whee"),
            ):
                _output_eq(
                    "inv -c parsing foo {}".format(argstr), expected + "\n"
                )
