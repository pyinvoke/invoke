import os
import sys
from functools import partial

from mock import patch, Mock, ANY
from spec import eq_, ok_, trap, skip, assert_contains, assert_not_contains

from invoke import (
    Program, Collection, ParseError, Task, FilesystemLoader, Executor, Context
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

        def env_prefix_defaults_to_INVOKE_(self):
            eq_(Program().env_prefix, 'INVOKE_')

        def env_prefix_can_be_overridden(self):
            eq_(Program(env_prefix='FOO_').env_prefix, 'FOO_')


    class miscellaneous:
        "miscellaneous behaviors"
        def debug_flag_activates_logging(self):
            # Have to patch our logger to get in before Nose logcapture kicks
            # in.
            with patch('invoke.util.debug') as debug:
                p = Program()
                p.search_collection_name = 'debugging'
                expect('-d foo', program=p)
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


    class load_collection:
        def complains_when_default_collection_not_found(self):
            # NOTE: assumes system under test has no tasks.py in root. Meh.
            with cd(ROOT):
                expect("foo", err="Can't find any collection named 'tasks'!\n")

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
        def should_show_core_usage_on_core_parse_failures(self):
            skip()

        def should_show_context_usage_on_context_parse_failures(self):
            skip()


