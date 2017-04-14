import os
import sys
from functools import partial

from mock import patch, Mock, ANY
from spec import eq_, ok_, trap, skip, assert_contains, assert_not_contains

from invoke import (
    Program, Collection, Task, FilesystemLoader, Executor, Config,
    UnexpectedExit, Result,
)
from invoke import main
from invoke.util import cd

from _util import (
    load, IntegrationSpec, expect, skip_if_windows,
)


ROOT = os.path.abspath(os.path.sep)


class Program_(IntegrationSpec):
    class init:
        "__init__"
        def may_specify_version(self):
            eq_(Program(version='1.2.3').version, '1.2.3')

        def default_version_is_unknown(self):
            eq_(Program().version, 'unknown')

        def may_specify_namespace(self):
            foo = load('foo')
            ok_(Program(namespace=foo).namespace is foo)

        def may_specify_name(self):
            eq_(Program(name='Myapp').name, 'Myapp')

        def may_specify_binary(self):
            eq_(Program(binary='myapp').binary, 'myapp')

        def loader_class_defaults_to_FilesystemLoader(self):
            ok_(Program().loader_class is FilesystemLoader)

        def may_specify_loader_class(self):
            klass = object()
            eq_(Program(loader_class=klass).loader_class, klass)

        def executor_class_defaults_to_Executor(self):
            ok_(Program().executor_class is Executor)

        def may_specify_executor_class(self):
            klass = object()
            eq_(Program(executor_class=klass).executor_class, klass) # noqa

        def config_class_defaults_to_Config(self):
            ok_(Program().config_class is Config)

        def may_specify_config_class(self):
            klass = object()
            eq_(Program(config_class=klass).config_class, klass) # noqa


    class miscellaneous:
        "miscellaneous behaviors"
        def debug_flag_activates_logging(self):
            # Have to patch our logger to get in before Nose logcapture kicks
            # in.
            with patch('invoke.util.debug') as debug:
                expect('-d -c debugging foo')
                debug.assert_called_with('my-sentinel')

        def bytecode_skipped_by_default(self):
            expect('-c foo mytask')
            eq_(sys.dont_write_bytecode, True)

        def write_pyc_explicitly_enables_bytecode_writing(self):
            expect('--write-pyc -c foo mytask')
            eq_(sys.dont_write_bytecode, False)


    class normalize_argv:
        @patch('invoke.program.sys')
        def defaults_to_sys_argv(self, mock_sys):
            argv = ['inv', '--version']
            mock_sys.argv = argv
            p = Program()
            p.print_version = Mock()
            p.run(exit=False)
            p.print_version.assert_called()

        def uses_a_list_unaltered(self):
            p = Program()
            p.print_version = Mock()
            p.run(['inv', '--version'], exit=False)
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
            expect("/usr/local/bin/myapp --version", out="Myapp unknown\n",
                invoke=False)

        def uses_overridden_value_when_given(self):
            p = Program(name='NotInvoke')
            expect("--version", out="NotInvoke unknown\n", program=p)


    class binary:
        def defaults_to_argv_when_None(self):
            expect(
                "myapp --help",
                out="myapp [--core-opts]",
                invoke=False,
                test=assert_contains
            )

        def uses_overridden_value_when_given(self):
            expect(
                "myapp --help",
                out="nope [--core-opts]",
                program=Program(binary='nope'),
                invoke=False,
                test=assert_contains
            )

        @trap
        def use_binary_basename_when_invoked_absolutely(self):
            Program().run("/usr/local/bin/myapp --help", exit=False)
            stdout = sys.stdout.getvalue()
            assert_contains(stdout, "myapp [--core-opts]")
            assert_not_contains(stdout, "/usr/local/bin")


    class print_version:
        def displays_name_and_version(self):
            expect(
                "--version",
                program=Program(name="MyProgram", version='0.1.0'),
                out="MyProgram 0.1.0\n"
            )


    class initial_context:
        def contains_truly_core_arguments_regardless_of_namespace_value(self):
            # Spot check. See integration-style --help tests for full argument
            # checkup.
            for program in (Program(), Program(namespace=Collection())):
                for arg in ('--complete', '--debug', '--warn-only', '--list'):
                    expect(
                        "--help",
                        program=program,
                        out=arg,
                        test=assert_contains
                    )

        def null_namespace_triggers_task_related_args(self):
            program = Program(namespace=None)
            for arg in program.task_args():
                expect(
                    "--help",
                    program=program,
                    out=arg.name,
                    test=assert_contains
                )

        def non_null_namespace_does_not_trigger_task_related_args(self):
            for arg in Program().task_args():
                expect(
                    "--help",
                    out=arg.name,
                    program=Program(namespace=Collection(mytask=Task(Mock()))),
                    test=assert_not_contains,
                )


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
            klass.assert_called_with(start=ANY)


    class execute:
        def uses_executor_class_given(self):
            klass = Mock()
            Program(executor_class=klass).run("myapp foo", exit=False)
            klass.assert_called_with(ANY, ANY, ANY)
            klass.return_value.execute.assert_called_with(ANY)

        def executor_is_given_access_to_core_args_and_remainder(self):
            klass = Mock()
            cmd = "myapp -e foo -- myremainder"
            Program(executor_class=klass).run(cmd, exit=False)
            core = klass.call_args[0][2]
            eq_(core[0].args['echo'].value, True)
            eq_(core.remainder, "myremainder")


    class core_args:
        def returns_core_args_list(self):
            # Mostly so we encode explicity doc'd public API member in tests.
            # Spot checks good enough, --help tests include the full deal.
            core_args = Program().core_args()
            core_arg_names = [x.names[0] for x in core_args]
            for name in ('complete', 'help', 'pty', 'version'):
                ok_(name in core_arg_names)
            # Also make sure it's a list for easier tweaking/appending
            ok_(isinstance(core_args, list))


    class run:
        # NOTE: some of these are integration-style tests, but they are still
        # fast tests (so not needing to go into the integration suite) and
        # touch on transformations to the command line that occur above, or
        # around, the actual parser classes/methods (thus not being suitable
        # for the parser's own unit tests).

        def seeks_and_loads_tasks_module_by_default(self):
            expect('foo', out="Hm\n")

        def does_not_seek_tasks_module_if_namespace_was_given(self):
            expect(
                'foo',
                err="No idea what 'foo' is!\n",
                program=Program(namespace=Collection('blank'))
            )

        def explicit_namespace_works_correctly(self):
            # Regression-ish test re #288
            ns = Collection.from_module(load('integration'))
            expect(
                'print_foo',
                out='foo\n',
                program=Program(namespace=ns),
            )

        def allows_explicit_task_module_specification(self):
            expect("-c integration print_foo", out="foo\n")

        def handles_task_arguments(self):
            expect("-c integration print_name --name inigo", out="inigo\n")

        @trap
        @patch('invoke.program.sys.exit')
        def ParseErrors_display_message_and_exit_1(self, mock_exit):
            p = Program()
            # Run with a definitely-parser-angering incorrect input; the fact
            # that this line doesn't raise an exception and thus fail the
            # test, is what we're testing...
            nah = 'nopenotvalidsorry'
            p.run("myapp {0}".format(nah))
            # Expect that we did print the core body of the ParseError (e.g.
            # "no idea what foo is!") and exit 1. (Intent is to display that
            # info w/o a full traceback, basically.)
            eq_(sys.stderr.getvalue(), "No idea what '{0}' is!\n".format(nah))
            mock_exit.assert_called_with(1)

        @trap
        @patch('invoke.program.sys.exit')
        def UnexpectedExit_exits_with_code_when_no_hiding(self, mock_exit):
            p = Program()
            oops = UnexpectedExit(Result(
                command='meh',
                exited=17,
                hide=tuple(),
            ))
            p.execute = Mock(side_effect=oops)
            p.run("myapp foo")
            # Expect NO repr printed, because stdout/err were not hidden, so we
            # don't want to add extra annoying verbosity - we want to be more
            # Make-like here.
            eq_(sys.stderr.getvalue(), "")
            # But we still exit with expected code (vs e.g. 1 or 0)
            mock_exit.assert_called_with(17)

        @trap
        @patch('invoke.program.sys.exit')
        def shows_UnexpectedExit_repr_when_streams_hidden(self, mock_exit):
            p = Program()
            oops = UnexpectedExit(Result(
                command='meh',
                exited=54,
                stdout='things!',
                stderr='ohnoz!',
                hide=('stdout', 'stderr'),
            ))
            p.execute = Mock(side_effect=oops)
            p.run("myapp foo")
            # Expect repr() of exception prints to stderr
            # NOTE: this partially duplicates a test in runners.py; whatever.
            eq_(sys.stderr.getvalue(), """Encountered a bad command exit code!

Command: 'meh'

Exit code: 54

Stdout:

things!

Stderr:

ohnoz!

""")
            # And exit with expected code (vs e.g. 1 or 0)
            mock_exit.assert_called_with(54)

        def should_show_core_usage_on_core_parse_failures(self):
            skip()

        def should_show_context_usage_on_context_parse_failures(self):
            skip()

        @trap
        @patch('invoke.program.sys.exit')
        def turns_KeyboardInterrupt_into_exit_code_1(self, mock_exit):
            p = Program()
            p.execute = Mock(side_effect=KeyboardInterrupt)
            p.run("myapp -c foo mytask")
            mock_exit.assert_called_with(1)


    class help_:
        "--help"

        class core:
            def empty_invocation_with_no_default_task_prints_help(self):
                expect("-c foo", out="Core options:", test=assert_contains)

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

  --complete                       Print tab-completion candidates for given
                                   parse remainder.
  --hide=STRING                    Set default value of run()'s 'hide' kwarg.
  --no-dedupe                      Disable task deduplication.
  --write-pyc                      Enable creation of .pyc files.
  -c STRING, --collection=STRING   Specify collection name to load.
  -d, --debug                      Enable debug output.
  -e, --echo                       Echo executed commands before running.
  -f STRING, --config=STRING       Runtime configuration file to use.
  -h [STRING], --help[=STRING]     Show core or per-task help and exit.
  -l, --list                       List available tasks.
  -p, --pty                        Use a pty when executing shell commands.
  -r STRING, --root=STRING         Change root directory used for finding task
                                   modules.
  -V, --version                    Show version and exit.
  -w, --warn-only                  Warn, instead of failing, when shell
                                   commands fail.

""".lstrip()
                for flag in ['-h', '--help']:
                    expect(flag, out=expected, program=main.program)

            def bundled_namespace_help_includes_subcommand_listing(self):
                t1, t2 = Task(Mock()), Task(Mock())
                coll = Collection(task1=t1, task2=t2)
                p = Program(namespace=coll)
                # Spot checks for expected bits, so we don't have to change
                # this every time core args change.
                for expected in (
                    # Usage line changes somewhat
                    "Usage: myapp [--core-opts] <subcommand> [--subcommand-opts] ...\n", # noqa
                    # Core options are still present
                    "Core options:\n",
                    "--echo",
                    # Subcommands are listed
                    "Subcommands:\n",
                    "  task1",
                    "  task2",
                ):
                    expect(
                        "myapp --help",
                        program=p,
                        invoke=False,
                        out=expected,
                        test=partial(assert_contains, escape=True)
                    )

            def core_help_doesnt_get_mad_if_loading_fails(self):
                # Expects no tasks.py in root of FS
                with cd(ROOT):
                    expect("--help", out="Usage: ", test=assert_contains)


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
                for flag in ['-h', '--help']:
                    expect('-c decorator {0} punch'.format(flag), out=expected)

            def works_for_unparameterized_tasks(self):
                expected = """
Usage: invoke [--core-opts] biz [other tasks here ...]

Docstring:
  none

Options:
  none

""".lstrip()
                expect('-c decorator -h biz', out=expected)

            def honors_program_binary(self):
                expect(
                    '-c decorator -h biz',
                    out="Usage: notinvoke",
                    test=assert_contains,
                    program=Program(binary='notinvoke')
                )

            def displays_docstrings_if_given(self):
                expected = """
Usage: invoke [--core-opts] foo [other tasks here ...]

Docstring:
  Foo the bar.

Options:
  none

""".lstrip()
                expect('-c decorator -h foo', out=expected)

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
                expect('-c decorator -h foo2', out=expected)

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
                expect('-c decorator -h foo3', out=expected)

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
                expect("-c decorator -h punch --list", out=expected)

            def complains_if_given_invalid_task_name(self):
                expect("-h this", err="No idea what 'this' is!\n")


    class task_list:
        "--list"

        def _listing(self, lines):
            return """
Available tasks:

{0}

""".format('\n'.join("  " + x for x in lines)).lstrip()

        def _list_eq(self, collection, listing):
            cmd = '-c {0} --list'.format(collection)
            expect(cmd, out=self._listing(listing))

        def simple_output(self):
            expected = self._listing((
                'bar',
                'biz',
                'boz',
                'foo',
                'post1',
                'post2',
                'print_foo',
                'print_name',
                'print_underscored_arg',
            ))
            for flag in ('-l', '--list'):
                expect('-c integration {0}'.format(flag), out=expected)

        def namespacing(self):
            self._list_eq('namespacing', (
                'toplevel',
                'module.mytask',
            ))

        def top_level_tasks_listed_first(self):
            self._list_eq('simple_ns_list', (
                'z_toplevel',
                'a.b.subtask'
            ))

        def subcollections_sorted_in_depth_order(self):
            self._list_eq('deeper_ns_list', (
                'toplevel',
                'a.subtask',
                'a.nother.subtask',
            ))

        def aliases_sorted_alphabetically(self):
            self._list_eq('alias_sorting', (
                'toplevel (a, z)',
            ))

        def default_tasks(self):
            # sub-ns default task display as "real.name (collection name)"
            self._list_eq('explicit_root', (
                'top_level (othertop)',
                'sub.sub_task (sub, sub.othersub)',
            ))

        def docstrings_shown_alongside(self):
            self._list_eq('docstrings', (
                'leading_whitespace    foo',
                'no_docstring',
                'one_line              foo',
                'two_lines             foo',
                'with_aliases (a, b)   foo',
            ))

        def docstrings_are_wrapped_to_terminal_width(self):
            self._list_eq('nontrivial_docstrings', (
                'no_docstring',
                'task_one       Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n                 Nullam id dictum', # noqa
                'task_two       Nulla eget ultrices ante. Curabitur sagittis commodo posuere.\n                 Duis dapibus', # noqa
            ))

        def empty_collections_say_no_tasks(self):
            expect(
                "-c empty -l",
                out="No tasks found in collection 'empty'!\n"
            )


    class run_options:
        "run() related CLI flags affect 'run' config values"
        def _test_flag(self, flag, key, value=True):
            p = Program()
            p.execute = Mock() # neuter
            p.run('inv {0} foo'.format(flag))
            eq_(p.config.run[key], value)

        def warn_only(self):
            self._test_flag('-w', 'warn')

        def pty(self):
            self._test_flag('-p', 'pty')

        def hide(self):
            self._test_flag('--hide both', 'hide', value='both')

        def echo(self):
            self._test_flag('-e', 'echo')


    class configuration:
        "Configuration-related concerns"

        @trap
        def config_class_init_kwarg_is_honored(self):
            klass = Mock()
            Program(config_class=klass).run("myapp foo", exit=False)
            eq_(len(klass.call_args_list), 1) # don't care about actual args

        @trap
        def config_attribute_is_memoized(self):
            klass = Mock()
            # Can't .config without .run (meh); .run calls .config once.
            p = Program(config_class=klass)
            p.run("myapp foo", exit=False)
            eq_(klass.call_count, 1)
            # Second access should use cached value
            p.config
            eq_(klass.call_count, 1)

        # NOTE: these tests all rely on the invoked tasks to perform the
        # necessary asserts.
        # TODO: can probably tighten these up to assert things about
        # Program.config instead?

        def per_project_config_files_are_loaded(self):
            with cd(os.path.join('configs', 'yaml')):
                expect("mytask")

        def per_project_config_files_load_with_explicit_ns(self):
            # Re: #234
            with cd(os.path.join('configs', 'yaml')):
                expect("-c explicit mytask")

        def runtime_config_file_honored(self):
            with cd('configs'):
                expect("-c runtime -f yaml/invoke.yaml mytask")

        def tasks_dedupe_honors_configuration(self):
            # Kinda-sorta duplicates some tests in executor.py, but eh.
            with cd('configs'):
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
""".lstrip())
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
""".lstrip())

        # * debug (top level?)
        # * hide (run.hide...lol)
        # * pty (run.pty)
        # * warn (run.warn)

        def env_vars_load_with_prefix(self):
            os.environ['INVOKE_RUN_ECHO'] = "1"
            expect('-c contextualized check_echo')

        def env_var_prefix_can_be_overridden(self):
            os.environ['MYAPP_RUN_HIDE'] = "both"
            # This forces the execution stuff, including Executor, to run
            # NOTE: it's not really possible to rework the impl so this test is
            # cleaner - tasks require per-task/per-collection config, which can
            # only be realized at the time a given task is to be executed.
            # Unless we overhaul the Program/Executor relationship so Program
            # does more of the heavy lifting re: task lookup/load/etc...
            # NOTE: check_hide will kaboom if its context's run.hide is not set
            # to True (default False).
            class MyConf(Config):
                env_prefix = 'MYAPP'
            p = Program(config_class=MyConf)
            p.run('inv -c contextualized check_hide')
