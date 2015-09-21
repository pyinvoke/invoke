import os
import sys
from functools import partial

from mock import patch, Mock, ANY
from spec import eq_, ok_, trap, skip, assert_contains, assert_not_contains

from invoke import (
    Program, Collection, ParseError, Task, FilesystemLoader, Executor,
)
from invoke import main
from invoke.util import cd

from _util import (
    load, IntegrationSpec, expect, skip_if_windows, SimpleFailure
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


    class miscellaneous:
        "miscellaneous behaviors"
        def debug_flag_activates_logging(self):
            # Have to patch our logger to get in before Nose logcapture kicks
            # in.
            with patch('invoke.util.debug') as debug:
                expect('-d -c debugging foo')
                debug.assert_called_with('my-sentinel')


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
                for arg in ('--complete', '--debug', '--warn-only'):
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
            with cd('implicit'):
                Program(executor_class=klass).run("myapp foo", exit=False)
            klass.assert_called_with(ANY, ANY)
            klass.return_value.execute.assert_called_with(ANY)


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
            with cd('implicit'):
                expect('foo', out="Hm\n")

        def does_not_seek_tasks_module_if_namespace_was_given(self):
            with cd('implicit'):
                expect(
                    'foo',
                    err="No idea what 'foo' is!\n",
                    program=Program(namespace=Collection('blank'))
                )

        def allows_explicit_task_module_specification(self):
            expect("-c integration print_foo", out="foo\n")

        def handles_task_arguments(self):
            expect("-c integration print_name --name inigo", out="inigo\n")

        @trap
        @patch('invoke.program.sys.exit')
        def expected_failure_types_dont_raise_exceptions(self, mock_exit):
            "expected failure types don't raise exceptions"
            for side_effect in (
                SimpleFailure,
                ParseError("boo!"),
            ):
                p = Program()
                p.execute = Mock(side_effect=side_effect)
                p.run("myapp -c foo mytask") # valid task name for parse step
                # Make sure we still exited fail-wise
                mock_exit.assert_called_with(1)

        def should_show_core_usage_on_core_parse_failures(self):
            skip()

        def should_show_context_usage_on_context_parse_failures(self):
            skip()


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

            def bundled_namspace_help_includes_subcommand_listing(self):
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

        def empty_collections_say_no_tasks(self):
            expect(
                "-c empty -l",
                out="No tasks found in collection 'empty'!\n"
            )


    class run_options:
        "run() related CLI flags affect 'run' config values"
        def _test_flag(self, flag, key, value=True):
            p = Program()
            p._execute = Mock() # neuter
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
