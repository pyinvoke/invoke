import json
import os
import sys

from invoke.util import six, Lexicon
from mock import patch, Mock, ANY
import pytest
from pytest import skip
from pytest_relaxed import trap

from invoke import (
    Argument,
    Collection,
    Config,
    Executor,
    FilesystemLoader,
    ParserContext,
    ParseResult,
    Program,
    Result,
    Task,
    UnexpectedExit,
)
from invoke import main
from invoke.util import cd
from invoke.config import merge_dicts

from _util import (
    ROOT,
    expect,
    load,
    run,
    skip_if_windows,
    support_file,
    support_path,
)


pytestmark = pytest.mark.usefixtures("integration")


class Program_:
    class init:
        "__init__"

        def may_specify_version(self):
            assert Program(version="1.2.3").version == "1.2.3"

        def default_version_is_unknown(self):
            assert Program().version == "unknown"

        def may_specify_namespace(self):
            foo = load("foo")
            assert Program(namespace=foo).namespace is foo

        def may_specify_name(self):
            assert Program(name="Myapp").name == "Myapp"

        def may_specify_binary(self):
            assert Program(binary="myapp").binary == "myapp"

        def loader_class_defaults_to_FilesystemLoader(self):
            assert Program().loader_class is FilesystemLoader

        def may_specify_loader_class(self):
            klass = object()
            assert Program(loader_class=klass).loader_class == klass

        def executor_class_defaults_to_Executor(self):
            assert Program().executor_class is Executor

        def may_specify_executor_class(self):
            klass = object()
            assert Program(executor_class=klass).executor_class == klass

        def config_class_defaults_to_Config(self):
            assert Program().config_class is Config

        def may_specify_config_class(self):
            klass = object()
            assert Program(config_class=klass).config_class == klass

    class miscellaneous:
        "miscellaneous behaviors"

        def debug_flag_activates_logging(self):
            # Have to patch our logger to get in before logcapture kicks in.
            with patch("invoke.util.debug") as debug:
                Program().run("invoke -d -c debugging foo")
                debug.assert_called_with("my-sentinel")

        def debug_honored_as_env_var_too(self, reset_environ):
            os.environ["INVOKE_DEBUG"] = "1"
            with patch("invoke.util.debug") as debug:
                # NOTE: no use of -d/--debug
                Program().run("invoke -c debugging foo")
                debug.assert_called_with("my-sentinel")

        def bytecode_skipped_by_default(self):
            expect("-c foo mytask")
            assert sys.dont_write_bytecode

        def write_pyc_explicitly_enables_bytecode_writing(self):
            expect("--write-pyc -c foo mytask")
            assert not sys.dont_write_bytecode

    class normalize_argv:
        @patch("invoke.program.sys")
        def defaults_to_sys_argv(self, mock_sys):
            argv = ["inv", "--version"]
            mock_sys.argv = argv
            p = Program()
            p.print_version = Mock()
            p.run(exit=False)
            p.print_version.assert_called()

        def uses_a_list_unaltered(self):
            p = Program()
            p.print_version = Mock()
            p.run(["inv", "--version"], exit=False)
            p.print_version.assert_called()

        def splits_a_string(self):
            p = Program()
            p.print_version = Mock()
            p.run("inv --version", exit=False)
            p.print_version.assert_called()

    class name:
        def defaults_to_capitalized_binary_when_None(self):
            expect("myapp --version", out="Myapp unknown\n", invoke=False)

        def benefits_from_binary_absolute_behavior(self):
            "benefits from binary()'s absolute path behavior"
            expect(
                "/usr/local/bin/myapp --version",
                out="Myapp unknown\n",
                invoke=False,
            )

        def uses_overridden_value_when_given(self):
            p = Program(name="NotInvoke")
            expect("--version", out="NotInvoke unknown\n", program=p)

    class binary:
        def defaults_to_argv_when_None(self):
            stdout, _ = run("myapp --help", invoke=False)
            assert "myapp [--core-opts]" in stdout

        def uses_overridden_value_when_given(self):
            stdout, _ = run(
                "myapp --help", invoke=False, program=Program(binary="nope")
            )
            assert "nope [--core-opts]" in stdout

        @trap
        def use_binary_basename_when_invoked_absolutely(self):
            Program().run("/usr/local/bin/myapp --help", exit=False)
            stdout = sys.stdout.getvalue()
            assert "myapp [--core-opts]" in stdout
            assert "/usr/local/bin" not in stdout

    class called_as:
        # NOTE: these tests are meh due to Program's lifecycle design
        # (attributes get modified during run(), such as things based on
        # observed argv). It's not great, but, whatever.
        @trap
        def is_the_whole_deal_when_just_a_name(self):
            p = Program()
            p.run("whatever --help", exit=False)
            assert p.called_as == "whatever"

        @trap
        def is_basename_when_given_a_path(self):
            p = Program()
            p.run("/usr/local/bin/whatever --help", exit=False)
            assert p.called_as == "whatever"

    class binary_names:
        # NOTE: this is currently only used for completion stuff, so we use
        # that to test. TODO: maybe make this more unit-y...
        def defaults_to_argv_when_None(self):
            stdout, _ = run("foo --print-completion-script zsh", invoke=False)
            assert " foo" in stdout

        def can_be_given_directly(self):
            program = Program(binary_names=["foo", "bar"])
            stdout, _ = run(
                "foo --print-completion-script zsh",
                invoke=False,
                program=program,
            )
            assert " foo bar" in stdout

    class print_version:
        def displays_name_and_version(self):
            expect(
                "--version",
                program=Program(name="MyProgram", version="0.1.0"),
                out="MyProgram 0.1.0\n",
            )

    class initial_context:
        def contains_truly_core_arguments_regardless_of_namespace_value(self):
            # Spot check. See integration-style --help tests for full argument
            # checkup.
            for program in (Program(), Program(namespace=Collection())):
                for arg in ("--complete", "--debug", "--warn-only", "--list"):
                    stdout, _ = run("--help", program=program)
                    assert arg in stdout

        def null_namespace_triggers_task_related_args(self):
            program = Program(namespace=None)
            for arg in program.task_args():
                stdout, _ = run("--help", program=program)
                assert arg.name in stdout

        def non_null_namespace_does_not_trigger_task_related_args(self):
            for arg in Program().task_args():
                program = Program(namespace=Collection(mytask=Task(Mock())))
                stdout, _ = run("--help", program=program)
                assert arg.name not in stdout

    class load_collection:
        def complains_when_default_collection_not_found(self):
            # NOTE: assumes system under test has no tasks.py in root. Meh.
            with cd(ROOT):
                expect("-l", err="Can't find any collection named 'tasks'!\n")

        def complains_when_explicit_collection_not_found(self):
            expect(
                "-c huhwhat -l",
                err="Can't find any collection named 'huhwhat'!\n",
            )

        @trap
        def uses_loader_class_given(self):
            klass = Mock(side_effect=FilesystemLoader)
            Program(loader_class=klass).run("myapp --help foo", exit=False)
            klass.assert_called_with(start=ANY, config=ANY)

    class execute:
        def uses_executor_class_given(self):
            klass = Mock()
            Program(executor_class=klass).run("myapp foo", exit=False)
            klass.assert_called_with(ANY, ANY, ANY)
            klass.return_value.execute.assert_called_with(ANY)

        def executor_class_may_be_overridden_via_configured_string(self):
            class ExecutorOverridingConfig(Config):
                @staticmethod
                def global_defaults():
                    defaults = Config.global_defaults()
                    path = "custom_executor.CustomExecutor"
                    merge_dicts(defaults, {"tasks": {"executor_class": path}})
                    return defaults

            mock = load("custom_executor").CustomExecutor
            p = Program(config_class=ExecutorOverridingConfig)
            p.run("myapp noop", exit=False)
            assert mock.assert_called
            assert mock.return_value.execute.called

        def executor_is_given_access_to_core_args_and_remainder(self):
            klass = Mock()
            cmd = "myapp -e foo -- myremainder"
            Program(executor_class=klass).run(cmd, exit=False)
            core = klass.call_args[0][2]
            assert core[0].args["echo"].value
            assert core.remainder == "myremainder"

    class core_args:
        def returns_core_args_list(self):
            # Mostly so we encode explicity doc'd public API member in tests.
            # Spot checks good enough, --help tests include the full deal.
            core_args = Program().core_args()
            core_arg_names = [x.names[0] for x in core_args]
            for name in ("complete", "help", "pty", "version"):
                assert name in core_arg_names
            # Also make sure it's a list for easier tweaking/appending
            assert isinstance(core_args, list)

    class args_property:
        def shorthand_for_self_core_args(self):
            "is shorthand for self.core[0].args"
            p = Program()
            p.run("myapp -e noop", exit=False)
            args = p.args
            assert isinstance(args, Lexicon)
            assert args.echo.value is True

    class core_args_from_task_contexts:
        # NOTE: many of these use Program.args in lieu of Program.core[0], for
        # convenience, tho also because initially the behavior was _in_ .args
        def core_context_gets_updated_with_core_flags_from_tasks(self):
            # Part of #466.
            p = Program()
            p.run("myapp -e noop --hide both", exit=False)
            # Was given in core
            assert p.args.echo.value is True
            # Was given in per-task
            assert p.args.hide.value == "both"

        def copying_from_task_context_does_not_set_empty_list_values(self):
            # Less of an issue for scalars, but for list-type args, doing
            # .value = <default value> actually ends up creating a
            # list-of-lists.
            p = Program()
            # Set up core-args parser context with an iterable arg that hasn't
            # seen any value yet
            def filename_args():
                return [Argument("filename", kind=list)]

            p.core = ParseResult([ParserContext(args=filename_args())])
            # And a core-via-tasks context with a copy of that same arg, which
            # also hasn't seen any value yet
            p.core_via_tasks = ParserContext(args=filename_args())
            # Now the behavior of .args can be tested as desired
            assert p.args["filename"].value == []  # Not [[]]!

        def copying_from_task_context_does_not_overwrite_good_values(self):
            # Another subcase, also mostly applying to list types: core context
            # got a useful value, nothing was found in the per-task context;
            # when a naive 'is not None' check is used, this overwrites the
            # good value with an empty list.
            # (Other types tend to not have this problem because their ._value
            # is always None when not set. TODO: maybe this should be
            # considered incorrect behavior for list type args?)
            def make_arg():
                return Argument("filename", kind=list)

            p = Program()
            # Core arg, which got a value
            arg = make_arg()
            arg.value = "some-file"  # appends to list
            p.core = ParseResult([ParserContext(args=[arg])])
            # Set core-via-tasks version to vanilla/blank/empty-list version
            p.core_via_tasks = ParserContext(args=[make_arg()])
            # Call .args, expect that the initial value was not overwritten
            assert p.args.filename.value == ["some-file"]

    class run:
        # NOTE: some of these are integration-style tests, but they are still
        # fast tests (so not needing to go into the integration suite) and
        # touch on transformations to the command line that occur above, or
        # around, the actual parser classes/methods (thus not being suitable
        # for the parser's own unit tests).

        def seeks_and_loads_tasks_module_by_default(self):
            expect("foo", out="Hm\n")

        def does_not_seek_tasks_module_if_namespace_was_given(self):
            expect(
                "foo",
                err="No idea what 'foo' is!\n",
                program=Program(namespace=Collection("blank")),
            )

        def explicit_namespace_works_correctly(self):
            # Regression-ish test re #288
            ns = Collection.from_module(load("integration"))
            expect("print-foo", out="foo\n", program=Program(namespace=ns))

        def allows_explicit_task_module_specification(self):
            expect("-c integration print-foo", out="foo\n")

        def handles_task_arguments(self):
            expect("-c integration print-name --name inigo", out="inigo\n")

        def can_change_collection_search_root(self):
            for flag in ("-r", "--search-root"):
                expect(
                    "{} branch/ alt-root".format(flag),
                    out="Down with the alt-root!\n",
                )

        def can_change_collection_search_root_with_explicit_module_name(self):
            for flag in ("-r", "--search-root"):
                expect(
                    "{} branch/ -c explicit lyrics".format(flag),
                    out="Don't swear!\n",
                )

        @trap
        @patch("invoke.program.sys.exit")
        def ParseErrors_display_message_and_exit_1(self, mock_exit):
            p = Program()
            # Run with a definitely-parser-angering incorrect input; the fact
            # that this line doesn't raise an exception and thus fail the
            # test, is what we're testing...
            nah = "nopenotvalidsorry"
            p.run("myapp {}".format(nah))
            # Expect that we did print the core body of the ParseError (e.g.
            # "no idea what foo is!") and exit 1. (Intent is to display that
            # info w/o a full traceback, basically.)
            stderr = sys.stderr.getvalue()
            assert stderr == "No idea what '{}' is!\n".format(nah)
            mock_exit.assert_called_with(1)

        @trap
        @patch("invoke.program.sys.exit")
        def UnexpectedExit_exits_with_code_when_no_hiding(self, mock_exit):
            p = Program()
            oops = UnexpectedExit(
                Result(command="meh", exited=17, hide=tuple())
            )
            p.execute = Mock(side_effect=oops)
            p.run("myapp foo")
            # Expect NO repr printed, because stdout/err were not hidden, so we
            # don't want to add extra annoying verbosity - we want to be more
            # Make-like here.
            assert sys.stderr.getvalue() == ""
            # But we still exit with expected code (vs e.g. 1 or 0)
            mock_exit.assert_called_with(17)

        @trap
        @patch("invoke.program.sys.exit")
        def shows_UnexpectedExit_str_when_streams_hidden(self, mock_exit):
            p = Program()
            oops = UnexpectedExit(
                Result(
                    command="meh",
                    exited=54,
                    stdout="things!",
                    stderr="ohnoz!",
                    encoding="utf-8",
                    hide=("stdout", "stderr"),
                )
            )
            p.execute = Mock(side_effect=oops)
            p.run("myapp foo")
            # Expect repr() of exception prints to stderr
            # NOTE: this partially duplicates a test in runners.py; whatever.
            stderr = sys.stderr.getvalue()
            expected = """Encountered a bad command exit code!

Command: 'meh'

Exit code: 54

Stdout:

things!

Stderr:

ohnoz!

"""
            assert stderr == expected
            # And exit with expected code (vs e.g. 1 or 0)
            mock_exit.assert_called_with(54)

        @trap
        @patch("invoke.program.sys.exit")
        def UnexpectedExit_str_encodes_stdout_and_err(self, mock_exit):
            p = Program()
            oops = UnexpectedExit(
                Result(
                    command="meh",
                    exited=54,
                    stdout=u"this is not ascii: \u1234",
                    stderr=u"this is also not ascii: \u4321",
                    encoding="utf-8",
                    hide=("stdout", "stderr"),
                )
            )
            p.execute = Mock(side_effect=oops)
            p.run("myapp foo")
            # NOTE: using explicit binary ASCII here, & accessing raw
            # getvalue() of the faked sys.stderr (spec.trap auto-decodes it
            # normally) to have a not-quite-tautological test. otherwise we'd
            # just be comparing unicode to unicode. shrug?
            expected = b"""Encountered a bad command exit code!

Command: 'meh'

Exit code: 54

Stdout:

this is not ascii: \xe1\x88\xb4

Stderr:

this is also not ascii: \xe4\x8c\xa1

"""
            got = six.BytesIO.getvalue(sys.stderr)
            assert got == expected

        def should_show_core_usage_on_core_parse_failures(self):
            skip()

        def should_show_context_usage_on_context_parse_failures(self):
            skip()

        @trap
        @patch("invoke.program.sys.exit")
        def turns_KeyboardInterrupt_into_exit_code_1(self, mock_exit):
            p = Program()
            p.execute = Mock(side_effect=KeyboardInterrupt)
            p.run("myapp -c foo mytask")
            mock_exit.assert_called_with(1)

    class help_:
        "--help"

        class core:
            def empty_invocation_with_no_default_task_prints_help(self):
                stdout, _ = run("-c foo")
                assert "Core options:" in stdout

            # TODO: On Windows, we don't get a pty, so we don't get a
            # guaranteed terminal size of 80x24. Skip for now, but maybe
            # a suitable fix would be to just strip all whitespace from the
            # returned and expected values before testing. Then terminal
            # size is ignored.
            @skip_if_windows
            def core_help_option_prints_core_help(self):
                # TODO: change dynamically based on parser contents?
                # e.g. no core args == no [--core-opts],
                # no tasks == no task stuff?
                # NOTE: test will trigger default pty size of 80x24, so the
                # below string is formatted appropriately.
                # TODO: add more unit-y tests for specific behaviors:
                # * fill terminal w/ columns + spacing
                # * line-wrap help text in its own column
                expected = """
Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

Core options:

  --complete                         Print tab-completion candidates for given
                                     parse remainder.
  --hide=STRING                      Set default value of run()'s 'hide' kwarg.
  --no-dedupe                        Disable task deduplication.
  --print-completion-script=STRING   Print the tab-completion script for your
                                     preferred shell (bash|zsh|fish).
  --prompt-for-sudo-password         Prompt user at start of session for the
                                     sudo.password config value.
  --write-pyc                        Enable creation of .pyc files.
  -c STRING, --collection=STRING     Specify collection name to load.
  -d, --debug                        Enable debug output.
  -D INT, --list-depth=INT           When listing tasks, only show the first
                                     INT levels.
  -e, --echo                         Echo executed commands before running.
  -f STRING, --config=STRING         Runtime configuration file to use.
  -F STRING, --list-format=STRING    Change the display format used when
                                     listing tasks. Should be one of: flat
                                     (default), nested, json.
  -h [STRING], --help[=STRING]       Show core or per-task help and exit.
  -l [STRING], --list[=STRING]       List available tasks, optionally limited
                                     to a namespace.
  -p, --pty                          Use a pty when executing shell commands.
  -r STRING, --search-root=STRING    Change root directory used for finding
                                     task modules.
  -R, --dry                          Echo commands instead of running.
  -T INT, --command-timeout=INT      Specify a global command execution
                                     timeout, in seconds.
  -V, --version                      Show version and exit.
  -w, --warn-only                    Warn, instead of failing, when shell
                                     commands fail.

""".lstrip()
                for flag in ["-h", "--help"]:
                    expect(flag, out=expected, program=main.program)

            def bundled_namespace_help_includes_subcommand_listing(self):
                t1, t2 = Task(Mock()), Task(Mock())
                coll = Collection(task1=t1, task2=t2)
                p = Program(namespace=coll)
                # Spot checks for expected bits, so we don't have to change
                # this every time core args change.
                for expected in (
                    # Usage line changes somewhat
                    "Usage: myapp [--core-opts] <subcommand> [--subcommand-opts] ...\n",  # noqa
                    # Core options are still present
                    "Core options:\n",
                    "--echo",
                    # Subcommands are listed
                    "Subcommands:\n",
                    "  task1",
                    "  task2",
                ):
                    stdout, _ = run("myapp --help", program=p, invoke=False)
                    assert expected in stdout

            def core_help_doesnt_get_mad_if_loading_fails(self):
                # Expects no tasks.py in root of FS
                with cd(ROOT):
                    stdout, _ = run("--help")
                    assert "Usage: " in stdout

        class per_task:
            "per-task"

            def prints_help_for_task_only(self):
                expected = """
Usage: invoke [--core-opts] punch [--options] [other tasks here ...]

Docstring:
  none

Options:
  -h STRING, --why=STRING   Motive
  -w STRING, --who=STRING   Who to punch

""".lstrip()
                for flag in ["-h", "--help"]:
                    expect("-c decorators {} punch".format(flag), out=expected)

            def works_for_unparameterized_tasks(self):
                expected = """
Usage: invoke [--core-opts] biz [other tasks here ...]

Docstring:
  none

Options:
  none

""".lstrip()
                expect("-c decorators -h biz", out=expected)

            def honors_program_binary(self):
                stdout, _ = run(
                    "-c decorators -h biz", program=Program(binary="notinvoke")
                )
                assert "Usage: notinvoke" in stdout

            def displays_docstrings_if_given(self):
                expected = """
Usage: invoke [--core-opts] foo [other tasks here ...]

Docstring:
  Foo the bar.

Options:
  none

""".lstrip()
                expect("-c decorators -h foo", out=expected)

            def dedents_correctly(self):
                expected = """
Usage: invoke [--core-opts] foo2 [other tasks here ...]

Docstring:
  Foo the bar:

    example code

  Added in 1.0

Options:
  none

""".lstrip()
                expect("-c decorators -h foo2", out=expected)

            def dedents_correctly_for_alt_docstring_style(self):
                expected = """
Usage: invoke [--core-opts] foo3 [other tasks here ...]

Docstring:
  Foo the other bar:

    example code

  Added in 1.1

Options:
  none

""".lstrip()
                expect("-c decorators -h foo3", out=expected)

            def exits_after_printing(self):
                # TODO: find & test the other variants of this error case, such
                # as core --help not exiting, --list not exiting, etc
                expected = """
Usage: invoke [--core-opts] punch [--options] [other tasks here ...]

Docstring:
  none

Options:
  -h STRING, --why=STRING   Motive
  -w STRING, --who=STRING   Who to punch

""".lstrip()
                expect("-c decorators -h punch --list", out=expected)

            def complains_if_given_invalid_task_name(self):
                expect("-h this", err="No idea what 'this' is!\n")

    class task_list:
        "--list"

        def _listing(self, lines):
            return """
Available tasks:

{}

""".format(
                "\n".join("  " + x for x in lines)
            ).lstrip()

        def _list_eq(self, collection, listing):
            cmd = "-c {} --list".format(collection)
            expect(cmd, out=self._listing(listing))

        def simple_output(self):
            expected = self._listing(
                (
                    "bar",
                    "biz",
                    "boz",
                    "foo",
                    "post1",
                    "post2",
                    "print-foo",
                    "print-name",
                    "print-underscored-arg",
                )
            )
            for flag in ("-l", "--list"):
                expect("-c integration {}".format(flag), out=expected)

        def namespacing(self):
            self._list_eq("namespacing", ("toplevel", "module.mytask"))

        def top_level_tasks_listed_first(self):
            self._list_eq("simple_ns_list", ("z-toplevel", "a.b.subtask"))

        def aliases_sorted_alphabetically(self):
            self._list_eq("alias_sorting", ("toplevel (a, z)",))

        def default_tasks(self):
            # sub-ns default task display as "real.name (collection name)"
            self._list_eq(
                "explicit_root",
                (
                    "top-level (other-top)",
                    "sub-level.sub-task (sub-level, sub-level.other-sub)",
                ),
            )

        def docstrings_shown_alongside(self):
            self._list_eq(
                "docstrings",
                (
                    "leading-whitespace    foo",
                    "no-docstring",
                    "one-line              foo",
                    "two-lines             foo",
                    "with-aliases (a, b)   foo",
                ),
            )

        def docstrings_are_wrapped_to_terminal_width(self):
            self._list_eq(
                "nontrivial_docstrings",
                (
                    "no-docstring",
                    "task-one       Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n                 Nullam id dictum",  # noqa
                    "task-two       Nulla eget ultrices ante. Curabitur sagittis commodo posuere.\n                 Duis dapibus",  # noqa
                ),
            )

        def empty_collections_say_no_tasks(self):
            expect(
                "-c empty -l", err="No tasks found in collection 'empty'!\n"
            )

        def nontrivial_trees_are_sorted_by_namespace_and_depth(self):
            # By using a larger sample, we can guard against unintuitive
            # behaviors arising from the above simple unit style tests. E.g.
            # earlier implementations 'broke up' collections that had more than
            # 2 levels of depth, because they displayed all 2nd-level tasks
            # before any 3rd-level ones.
            # The code must square that concern against "show shallow tasks
            # before deep ones" (vs straight up alpha sorting)
            expected = """Available tasks:

  shell (ipython)                       Load a REPL with project state already
                                        set up.
  test (run-tests)                      Run the test suite with baked-in args.
  build.all (build, build.everything)   Build all necessary artifacts.
  build.c-ext (build.ext)               Build our internal C extension.
  build.zap                             A silly way to clean.
  build.docs.all (build.docs)           Build all doc formats.
  build.docs.html                       Build HTML output only.
  build.docs.pdf                        Build PDF output only.
  build.python.all (build.python)       Build all Python packages.
  build.python.sdist                    Build classic style tar.gz.
  build.python.wheel                    Build a wheel.
  deploy.db (deploy.db-servers)         Deploy to our database servers.
  deploy.everywhere (deploy)            Deploy to all targets.
  deploy.web                            Update and bounce the webservers.
  provision.db                          Stand up one or more DB servers.
  provision.web                         Stand up a Web server.

Default task: test

"""
            stdout, _ = run("-c tree --list")
            assert expected == stdout

        class namespace_limiting:
            def argument_limits_display_to_given_namespace(self):
                stdout, _ = run("-c tree --list build")
                expected = """Available 'build' tasks:

  .all (.everything)      Build all necessary artifacts.
  .c-ext (.ext)           Build our internal C extension.
  .zap                    A silly way to clean.
  .docs.all (.docs)       Build all doc formats.
  .docs.html              Build HTML output only.
  .docs.pdf               Build PDF output only.
  .python.all (.python)   Build all Python packages.
  .python.sdist           Build classic style tar.gz.
  .python.wheel           Build a wheel.

Default 'build' task: .all

"""
                assert expected == stdout

            def argument_may_be_a_nested_namespace(self):
                stdout, _ = run("-c tree --list build.docs")
                expected = """Available 'build.docs' tasks:

  .all    Build all doc formats.
  .html   Build HTML output only.
  .pdf    Build PDF output only.

Default 'build.docs' task: .all

"""
                assert expected == stdout

            def empty_namespaces_say_no_tasks_in_namespace(self):
                # In other words, outer namespace may not be empty, but the
                # inner one is - this should act just like when there is no
                # namespace explicitly requested and there's no tasks.
                # TODO: should the name in the error message be the fully
                # qualified one instead?
                expect(
                    "-c empty_subcollection -l subcollection",
                    err="No tasks found in collection 'subcollection'!\n",  # noqa
                )

            def invalid_namespaces_exit_with_message(self):
                expect(
                    "-c empty -l nope",
                    err="Sub-collection 'nope' not found!\n",
                )

        class depth_limiting:
            def limits_display_to_given_depth(self):
                # Base case: depth=1 aka "show me the namespaces"
                expected = """Available tasks (depth=1):

  shell (ipython)                  Load a REPL with project state already set
                                   up.
  test (run-tests)                 Run the test suite with baked-in args.
  build [3 tasks, 2 collections]   Tasks for compiling static code and assets.
  deploy [3 tasks]                 How to deploy our code and configs.
  provision [2 tasks]              System setup code.

Default task: test

"""
                stdout, _ = run("-c tree --list -F flat --list-depth 1")
                assert expected == stdout

            def non_base_case(self):
                # Middle case: depth=2
                expected = """Available tasks (depth=2):

  shell (ipython)                       Load a REPL with project state already
                                        set up.
  test (run-tests)                      Run the test suite with baked-in args.
  build.all (build, build.everything)   Build all necessary artifacts.
  build.c-ext (build.ext)               Build our internal C extension.
  build.zap                             A silly way to clean.
  build.docs [3 tasks]                  Tasks for managing Sphinx docs.
  build.python [3 tasks]                PyPI/etc distribution artifacts.
  deploy.db (deploy.db-servers)         Deploy to our database servers.
  deploy.everywhere (deploy)            Deploy to all targets.
  deploy.web                            Update and bounce the webservers.
  provision.db                          Stand up one or more DB servers.
  provision.web                         Stand up a Web server.

Default task: test

"""
                stdout, _ = run("-c tree --list --list-depth=2")
                assert expected == stdout

            def depth_can_be_deeper_than_real_depth(self):
                # Edge case: depth > actual depth = same as no depth arg
                expected = """Available tasks (depth=5):

  shell (ipython)                       Load a REPL with project state already
                                        set up.
  test (run-tests)                      Run the test suite with baked-in args.
  build.all (build, build.everything)   Build all necessary artifacts.
  build.c-ext (build.ext)               Build our internal C extension.
  build.zap                             A silly way to clean.
  build.docs.all (build.docs)           Build all doc formats.
  build.docs.html                       Build HTML output only.
  build.docs.pdf                        Build PDF output only.
  build.python.all (build.python)       Build all Python packages.
  build.python.sdist                    Build classic style tar.gz.
  build.python.wheel                    Build a wheel.
  deploy.db (deploy.db-servers)         Deploy to our database servers.
  deploy.everywhere (deploy)            Deploy to all targets.
  deploy.web                            Update and bounce the webservers.
  provision.db                          Stand up one or more DB servers.
  provision.web                         Stand up a Web server.

Default task: test

"""
                stdout, _ = run("-c tree --list --list-depth=5")
                assert expected == stdout

            def works_with_explicit_namespace(self):
                expected = """Available 'build' tasks (depth=1):

  .all (.everything)   Build all necessary artifacts.
  .c-ext (.ext)        Build our internal C extension.
  .zap                 A silly way to clean.
  .docs [3 tasks]      Tasks for managing Sphinx docs.
  .python [3 tasks]    PyPI/etc distribution artifacts.

Default 'build' task: .all

"""
                stdout, _ = run("-c tree --list build --list-depth=1")
                assert expected == stdout

            def short_flag_is_D(self):
                expected = """Available tasks (depth=1):

  shell (ipython)                  Load a REPL with project state already set
                                   up.
  test (run-tests)                 Run the test suite with baked-in args.
  build [3 tasks, 2 collections]   Tasks for compiling static code and assets.
  deploy [3 tasks]                 How to deploy our code and configs.
  provision [2 tasks]              System setup code.

Default task: test

"""
                stdout, _ = run("-c tree --list --list-format=flat -D 1")
                assert expected == stdout

            def depth_of_zero_is_same_as_max_depth(self):
                expected = """Available tasks:

  shell (ipython)                       Load a REPL with project state already
                                        set up.
  test (run-tests)                      Run the test suite with baked-in args.
  build.all (build, build.everything)   Build all necessary artifacts.
  build.c-ext (build.ext)               Build our internal C extension.
  build.zap                             A silly way to clean.
  build.docs.all (build.docs)           Build all doc formats.
  build.docs.html                       Build HTML output only.
  build.docs.pdf                        Build PDF output only.
  build.python.all (build.python)       Build all Python packages.
  build.python.sdist                    Build classic style tar.gz.
  build.python.wheel                    Build a wheel.
  deploy.db (deploy.db-servers)         Deploy to our database servers.
  deploy.everywhere (deploy)            Deploy to all targets.
  deploy.web                            Update and bounce the webservers.
  provision.db                          Stand up one or more DB servers.
  provision.web                         Stand up a Web server.

Default task: test

"""
                stdout, _ = run("-c tree --list --list-format=flat -D 0")
                assert expected == stdout

        class format:
            def flat_is_legacy_default_format(self):
                # Sanity test that --list --list-format=flat is the same as the
                # old "just --list".
                expected = """Available tasks:

  shell (ipython)                       Load a REPL with project state already
                                        set up.
  test (run-tests)                      Run the test suite with baked-in args.
  build.all (build, build.everything)   Build all necessary artifacts.
  build.c-ext (build.ext)               Build our internal C extension.
  build.zap                             A silly way to clean.
  build.docs.all (build.docs)           Build all doc formats.
  build.docs.html                       Build HTML output only.
  build.docs.pdf                        Build PDF output only.
  build.python.all (build.python)       Build all Python packages.
  build.python.sdist                    Build classic style tar.gz.
  build.python.wheel                    Build a wheel.
  deploy.db (deploy.db-servers)         Deploy to our database servers.
  deploy.everywhere (deploy)            Deploy to all targets.
  deploy.web                            Update and bounce the webservers.
  provision.db                          Stand up one or more DB servers.
  provision.web                         Stand up a Web server.

Default task: test

"""
                stdout, _ = run("-c tree --list --list-format=flat")
                assert expected == stdout

            class nested:
                def base_case(self):
                    expected = """Available tasks ('*' denotes collection defaults):

  shell (ipython)           Load a REPL with project state already set up.
  test* (run-tests)         Run the test suite with baked-in args.
  build                     Tasks for compiling static code and assets.
      .all* (.everything)   Build all necessary artifacts.
      .c-ext (.ext)         Build our internal C extension.
      .zap                  A silly way to clean.
      .docs                 Tasks for managing Sphinx docs.
          .all*             Build all doc formats.
          .html             Build HTML output only.
          .pdf              Build PDF output only.
      .python               PyPI/etc distribution artifacts.
          .all*             Build all Python packages.
          .sdist            Build classic style tar.gz.
          .wheel            Build a wheel.
  deploy                    How to deploy our code and configs.
      .db (.db-servers)     Deploy to our database servers.
      .everywhere*          Deploy to all targets.
      .web                  Update and bounce the webservers.
  provision                 System setup code.
      .db                   Stand up one or more DB servers.
      .web                  Stand up a Web server.

Default task: test

"""
                    stdout, _ = run("-c tree -l -F nested")
                    assert expected == stdout

                def honors_namespace_arg_to_list(self):
                    stdout, _ = run("-c tree --list build -F nested")
                    expected = """Available 'build' tasks ('*' denotes collection defaults):

  .all* (.everything)   Build all necessary artifacts.
  .c-ext (.ext)         Build our internal C extension.
  .zap                  A silly way to clean.
  .docs                 Tasks for managing Sphinx docs.
      .all*             Build all doc formats.
      .html             Build HTML output only.
      .pdf              Build PDF output only.
  .python               PyPI/etc distribution artifacts.
      .all*             Build all Python packages.
      .sdist            Build classic style tar.gz.
      .wheel            Build a wheel.

Default 'build' task: .all

"""
                    assert expected == stdout

                def honors_depth_arg(self):
                    expected = """Available tasks (depth=2; '*' denotes collection defaults):

  shell (ipython)           Load a REPL with project state already set up.
  test* (run-tests)         Run the test suite with baked-in args.
  build                     Tasks for compiling static code and assets.
      .all* (.everything)   Build all necessary artifacts.
      .c-ext (.ext)         Build our internal C extension.
      .zap                  A silly way to clean.
      .docs [3 tasks]       Tasks for managing Sphinx docs.
      .python [3 tasks]     PyPI/etc distribution artifacts.
  deploy                    How to deploy our code and configs.
      .db (.db-servers)     Deploy to our database servers.
      .everywhere*          Deploy to all targets.
      .web                  Update and bounce the webservers.
  provision                 System setup code.
      .db                   Stand up one or more DB servers.
      .web                  Stand up a Web server.

Default task: test

"""
                    stdout, _ = run("-c tree -l -F nested --list-depth 2")
                    assert expected == stdout

                def depth_arg_deeper_than_real_depth(self):
                    expected = """Available tasks (depth=5; '*' denotes collection defaults):

  shell (ipython)           Load a REPL with project state already set up.
  test* (run-tests)         Run the test suite with baked-in args.
  build                     Tasks for compiling static code and assets.
      .all* (.everything)   Build all necessary artifacts.
      .c-ext (.ext)         Build our internal C extension.
      .zap                  A silly way to clean.
      .docs                 Tasks for managing Sphinx docs.
          .all*             Build all doc formats.
          .html             Build HTML output only.
          .pdf              Build PDF output only.
      .python               PyPI/etc distribution artifacts.
          .all*             Build all Python packages.
          .sdist            Build classic style tar.gz.
          .wheel            Build a wheel.
  deploy                    How to deploy our code and configs.
      .db (.db-servers)     Deploy to our database servers.
      .everywhere*          Deploy to all targets.
      .web                  Update and bounce the webservers.
  provision                 System setup code.
      .db                   Stand up one or more DB servers.
      .web                  Stand up a Web server.

Default task: test

"""
                    stdout, _ = run("-c tree -l -F nested --list-depth 5")
                    assert expected == stdout

                def all_possible_options(self):
                    expected = """Available 'build' tasks (depth=1; '*' denotes collection defaults):

  .all* (.everything)   Build all necessary artifacts.
  .c-ext (.ext)         Build our internal C extension.
  .zap                  A silly way to clean.
  .docs [3 tasks]       Tasks for managing Sphinx docs.
  .python [3 tasks]     PyPI/etc distribution artifacts.

Default 'build' task: .all

"""
                    stdout, _ = run("-c tree -l build -F nested -D1")
                    assert expected == stdout

                # TODO: having these in each format smells like a POSSIBLY good
                # use for parameterized tests...
                def empty_namespaces_say_no_tasks_in_namespace(self):
                    expect(
                        "-c empty_subcollection -l subcollection -F nested",
                        err="No tasks found in collection 'subcollection'!\n",
                    )

                def invalid_namespaces_exit_with_message(self):
                    expect(
                        "-c empty -l nope -F nested",
                        err="Sub-collection 'nope' not found!\n",
                    )

            class json:
                def setup(self):
                    # Stored expected data as an actual JSON file cuz it's big
                    # & looks like crap if inlined. Plus by round-tripping it
                    # we remove the pretty-printing. Win-win?
                    self.tree = json.loads(support_file("tree.json"))
                    self.by_name = {
                        x["name"]: x for x in self.tree["collections"]
                    }

                def base_case(self):
                    stdout, _ = run("-c tree --list --list-format=json")
                    assert self.tree == json.loads(stdout)

                def honors_namespace_arg_to_list(self):
                    stdout, _ = run("-c tree --list deploy --list-format=json")
                    expected = self.by_name["deploy"]
                    assert expected == json.loads(stdout)

                def does_not_honor_depth_arg(self):
                    _, stderr = run("-c tree -l --list-format json -D 2")
                    expected = "The --list-depth option is not supported with JSON format!\n"  # noqa
                    assert expected == stderr

                def does_not_honor_depth_arg_even_with_namespace(self):
                    _, stderr = run("-c tree -l build -F json -D 2")
                    expected = "The --list-depth option is not supported with JSON format!\n"  # noqa
                    assert expected == stderr

                # TODO: should an empty-but-valid namespace in JSON format
                # actually just be an empty dict instead? Let's stay consistent
                # with the other formats for now, but...
                def empty_namespaces_say_no_tasks_in_namespace(self):
                    expect(
                        "-c empty_subcollection -l subcollection -F nested",
                        err="No tasks found in collection 'subcollection'!\n",  # noqa
                    )

                # NOTE: this should probably still exit with a message even if
                # the previous test re: valid-but-empty is determined to want a
                # non-error behavior.
                def invalid_namespaces_exit_with_message(self):
                    expect(
                        "-c empty -l nope -F nested",
                        err="Sub-collection 'nope' not found!\n",
                    )

    class run_options:
        "run() related CLI flags affect 'run' config values"

        def _test_flag(self, flag, key, value=True):
            p = Program()
            p.execute = Mock()  # neuter
            p.run("inv {} foo".format(flag))
            assert p.config.run[key] == value

        def warn_only(self):
            self._test_flag("-w", "warn")

        def pty(self):
            self._test_flag("-p", "pty")

        def hide(self):
            self._test_flag("--hide both", "hide", value="both")

        def echo(self):
            self._test_flag("-e", "echo")

        def timeout(self):
            for flag in ("-T", "--command-timeout"):
                p = Program()
                p.execute = Mock()  # neuter
                p.run("inv {} 5 foo".format(flag))
                assert p.config.timeouts.command == 5

    class configuration:
        "Configuration-related concerns"

        def _klass(self):
            # Pauper's mock that can honor .tasks.collection_name (Loader
            # looks in the config for this by default.)
            instance_mock = Mock(
                tasks=Mock(collection_name="whatever", search_root="meh")
            )
            return Mock(return_value=instance_mock)

        @trap
        def config_class_init_kwarg_is_honored(self):
            klass = self._klass()
            Program(config_class=klass).run("myapp foo", exit=False)
            # Don't care about actual args...
            assert len(klass.call_args_list) == 1

        @trap
        def config_attribute_is_memoized(self):
            klass = self._klass()
            # Can't .config without .run (meh); .run calls .config once.
            p = Program(config_class=klass)
            p.run("myapp foo", exit=False)
            assert klass.call_count == 1
            # Second access should use cached value
            p.config
            assert klass.call_count == 1

        # NOTE: these tests all rely on the invoked tasks to perform the
        # necessary asserts.
        # TODO: can probably tighten these up to assert things about
        # Program.config instead?

        def per_project_config_files_are_loaded_before_task_parsing(self):
            # Relies on auto_dash_names being loaded at project-conf level;
            # fixes #467; when bug present, project conf is loaded _after_
            # attempt to parse tasks, causing explosion when i_have_underscores
            # is only sent to parser as i-have-underscores.
            with cd(os.path.join("configs", "underscores")):
                expect("i_have_underscores")

        def per_project_config_files_load_with_explicit_ns(self):
            # Re: #234
            with cd(os.path.join("configs", "yaml")):
                expect("-c explicit mytask")

        class runtime_config_file:
            def can_be_set_via_cli_option(self):
                with cd("configs"):
                    expect("-c runtime -f yaml/invoke.yaml mytask")

            def can_be_set_via_env(self, reset_environ):
                os.environ["INVOKE_RUNTIME_CONFIG"] = "yaml/invoke.yaml"
                with cd("configs"):
                    expect("-c runtime mytask")

            def cli_option_wins_over_env(self, reset_environ):
                # Set env var to load the JSON config instead of the YAML one,
                # which contains a "json" string internally.
                os.environ["INVOKE_RUNTIME_CONFIG"] = "json/invoke.json"
                with cd("configs"):
                    # But run the default test task, which expects a "yaml"
                    # string. If the env var won, this would explode.
                    expect("-c runtime -f yaml/invoke.yaml mytask")

        def tasks_dedupe_honors_configuration(self):
            # Kinda-sorta duplicates some tests in executor.py, but eh.
            with cd("configs"):
                # Runtime conf file
                expect(
                    "-c integration -f no-dedupe.yaml biz",
                    out="""
foo
foo
bar
biz
post1
post2
post2
""".lstrip(),
                )
                # Flag beats runtime
                expect(
                    "-c integration -f dedupe.yaml --no-dedupe biz",
                    out="""
foo
foo
bar
biz
post1
post2
post2
""".lstrip(),
                )

        # * debug (top level?)
        # * hide (run.hide...lol)
        # * pty (run.pty)
        # * warn (run.warn)

        def env_vars_load_with_prefix(self, monkeypatch):
            monkeypatch.setenv("INVOKE_RUN_ECHO", "1")
            expect("-c contextualized check-echo")

        def env_var_prefix_can_be_overridden(self, monkeypatch):
            monkeypatch.setenv("MYAPP_RUN_HIDE", "both")
            # This forces the execution stuff, including Executor, to run
            # NOTE: it's not really possible to rework the impl so this test is
            # cleaner - tasks require per-task/per-collection config, which can
            # only be realized at the time a given task is to be executed.
            # Unless we overhaul the Program/Executor relationship so Program
            # does more of the heavy lifting re: task lookup/load/etc...
            # NOTE: check-hide will kaboom if its context's run.hide is not set
            # to True (default False).
            class MyConf(Config):
                env_prefix = "MYAPP"

            p = Program(config_class=MyConf)
            p.run("inv -c contextualized check-hide")

    class other_behavior:
        @patch("invoke.program.getpass.getpass")
        def sudo_prompt_up_front(self, getpass):
            getpass.return_value = "mypassword"
            # Task under test makes expectations re: sudo config (doesn't
            # actually even sudo, sudo's use of config is tested in Config
            # tests)
            with support_path():
                try:
                    Program().run(
                        "inv --prompt-for-sudo-password -c sudo_prompt expect-config"  # noqa
                    )
                except SystemExit as e:
                    # If inner call failed, we'll already have seen its output,
                    # and this will just ensure we ourselves are marked failed
                    assert e.code == 0
            # Sanity check that getpass spat out desired prompt
            prompt = "Desired 'sudo.password' config value: "
            getpass.assert_called_once_with(prompt)
