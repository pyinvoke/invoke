import os
import sys
from functools import partial

from mock import patch, Mock, ANY
from spec import eq_, ok_, trap, skip, assert_contains, assert_not_contains

from invoke import (
    Program, Collection, ParseError, Task, FilesystemLoader, Executor, Context
)
from invoke.main import InvokeProgram
from invoke import main
from invoke.util import cd

from _util import (
    load, IntegrationSpec, expect_inv, expect, skip_if_windows, SimpleFailure
)


ROOT = os.path.abspath(os.path.sep)

class InvokeProgram_(IntegrationSpec):
    class initial_context:
        def adds_additional_task_related_args_to_help(self):
            program = InvokeProgram(namespace=None)
            # have the task_args attr get set by the overridden core_args
            program.core_args()
            for arg in program.task_args:
                expect(
                    "--help",
                    program=program,
                    out=arg.name,
                    test=assert_contains
                )

        def complains_when_default_collection_not_found(self):
            # NOTE: assumes system under test has no tasks.py in root. Meh.
            with cd(ROOT):
                expect_inv("-l", err="Can't find any collection named 'tasks'!\n")

        def complains_when_explicit_collection_not_found(self):
            expect_inv(
                "-c huhwhat -l",
                err="Can't find any collection named 'huhwhat'!\n",
            )

    class core_args:
        def returns_core_args_list_extended(self):
            # Mostly so we encode explicity doc'd public API member in tests.
            # Spot checks good enough, --help tests include the full deal.
            core_args = InvokeProgram().core_args()
            core_arg_names = [x.names[0] for x in core_args]
            for name in ('list', 'collection', 'no-dedupe', 'root'):
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
            with cd('implicit'):
                expect_inv('foo', out="Hm\n")

        def does_not_seek_tasks_module_if_namespace_was_given(self):
            with cd('implicit'):
                expect(
                    'foo',
                    err="No idea what 'foo' is!\n",
                    program=InvokeProgram(namespace=Collection('blank'))
                )

        def allows_explicit_task_module_specification(self):
            expect_inv("-c integration print_foo", out="foo\n")

        def handles_task_arguments(self):
            expect_inv("-c integration print_name --name inigo", out="inigo\n")

        @trap
        @patch('invoke.program.sys.exit')
        def expected_failure_types_dont_raise_exceptions(self, mock_exit):
            "expected failure types don't raise exceptions"
            for side_effect in (
                SimpleFailure,
                ParseError("boo!"),
            ):
                p = InvokeProgram()
                p.execute = Mock(side_effect=side_effect)
                p.run("myapp -c foo mytask") # valid task name for parse step
                # Make sure we still exited fail-wise
                mock_exit.assert_called_with(1)


    class help_:
        "--help"

        class core:
            def empty_invocation_with_no_default_task_prints_help(self):
                expect_inv("-c foo", out="Core options:", test=assert_contains)

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
                    expect_inv(flag, out=expected, program=main.program)

            def bundled_namspace_help_includes_subcommand_listing(self):
                t1, t2 = Task(Mock()), Task(Mock())
                coll = Collection(task1=t1, task2=t2)
                p = InvokeProgram(namespace=coll)
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
                    expect_inv(
                        "myapp --help",
                        program=p,
                        invoke=False,
                        out=expected,
                        test=partial(assert_contains, escape=True)
                    )

            def core_help_doesnt_get_mad_if_loading_fails(self):
                # Expects no tasks.py in root of FS
                with cd(ROOT):
                    expect_inv("--help", out="Usage: ", test=assert_contains)


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
                    expect_inv('-c decorator {0} punch'.format(flag), out=expected)

            def works_for_unparameterized_tasks(self):
                expected = """
Usage: invoke [--core-opts] biz [other tasks here ...]

Docstring:
  none

Options:
  none

""".lstrip()
                expect_inv('-c decorator -h biz', out=expected)

            def honors_program_binary(self):
                expect_inv(
                    '-c decorator -h biz',
                    out="Usage: notinvoke",
                    test=assert_contains,
                    program=InvokeProgram(binary='notinvoke')
                )

            def displays_docstrings_if_given(self):
                expected = """
Usage: invoke [--core-opts] foo [other tasks here ...]

Docstring:
  Foo the bar.

Options:
  none

""".lstrip()
                expect_inv('-c decorator -h foo', out=expected)

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
                expect_inv('-c decorator -h foo2', out=expected)

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
                expect_inv('-c decorator -h foo3', out=expected)

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
                expect_inv("-c decorator -h punch --list", out=expected)

            def complains_if_given_invalid_task_name(self):
                expect_inv("-h this", err="No idea what 'this' is!\n")


    class task_list:
        "--list"

        def _listing(self, lines):
            return """
Available tasks:

{0}

""".format('\n'.join("  " + x for x in lines)).lstrip()

        def _list_eq(self, collection, listing):
            cmd = '-c {0} --list'.format(collection)
            expect_inv(cmd, out=self._listing(listing))

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
                expect_inv('-c integration {0}'.format(flag), out=expected)

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

        def empty_collections_say_no_tasks(self):
            expect_inv(
                "-c empty -l",
                out="No tasks found in collection 'empty'!\n"
            )


    class run_options:
        "run() related CLI flags affect 'run' config values"
        def _test_flag(self, flag, key, value=True):
            p = InvokeProgram()
            p.execute = Mock() # neuter
            with cd('implicit'):
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

        # NOTE: these tests all rely on the invoked tasks to perform the
        # necessary asserts.
        # TODO: can probably tighten these up to assert things about
        # Program.config instead?

        def per_project_config_files_are_loaded(self):
            with cd(os.path.join('configs', 'yaml')):
                expect_inv("mytask")

        def per_project_config_files_load_with_explicit_ns(self):
            # Re: #234
            with cd(os.path.join('configs', 'yaml')):
                expect_inv("-c explicit mytask")

        def runtime_config_file_honored(self):
            with cd('configs'):
                expect_inv("-c runtime -f yaml/invoke.yaml mytask")

        def tasks_dedupe_honors_configuration(self):
            # Kinda-sorta duplicates some tests in executor.py, but eh.
            with cd('configs'):
                # Runtime conf file
                expect_inv(
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
                expect_inv(
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
            expect_inv('-c contextualized check_echo')

        @patch('invoke.executor.Context', side_effect=Context)
        def env_var_prefix_can_be_overridden(self, context_class):
            os.environ['MYAPP_RUN_ECHO'] = "1"
            # This forces the execution stuff, including Executor, to run
            # NOTE: it's not really possible to rework the impl so this test is
            # cleaner - tasks require per-task/per-collection config, which can
            # only be realized at the time a given task is to be executed.
            # Unless we overhaul the Program/Executor relationship so Program
            # does more of the heavy lifting re: task lookup/load/etc...
            InvokeProgram(env_prefix='MYAPP_').run('inv -c contextualized go')
            # Check the config obj handed from Executor to Context
            eq_(context_class.call_args[1]['config'].run.echo, True)
