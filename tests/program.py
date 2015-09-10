import sys

from mock import patch, Mock
from spec import Spec, eq_, ok_, raises, skip, trap

from invoke import Program, Collection

from _utils import load, expect_exit


class Program_(Spec):
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

    class normalize_argv:
        @patch('invoke.program.sys')
        def defaults_to_sys_argv(self, mock_sys):
            argv = ['inv', '--version']
            mock_sys.argv = argv
            p = Program()
            p.print_version = Mock()
            p.run()
            p.print_version.assert_called()

        def uses_a_list_unaltered(self):
            p = Program()
            p.print_version = Mock()
            p.run(['inv', '--version'], exit=False)
            p.print_version.assert_called()

        def splits_a_string(self):
            eq_(Program().normalize_argv("foo bar"), ['foo', 'bar'])

    class normalize_name:
        @trap
        def defaults_to_capitalized_argv_when_None(self):
            Program().run("myapp --version", exit=False)
            eq_(sys.stdout.getvalue(), "Myapp unknown\n")

        @trap
        def uses_overridden_value_when_given(self):
            Program(name='NotProgram').run("program --version", exit=False)
            eq_(sys.stdout.getvalue(), "NotProgram unknown\n")

    class normalize_binary:
        @trap
        def defaults_to_argv_when_None(self):
            Program().run("myapp --help", exit=False)
            ok_("myapp [--core-opts]" in sys.stdout.getvalue())

        @trap
        def use_binary_basename_when_invoked_absolutely(self):
            Program().run("/usr/local/bin/myapp --help", exit=False)
            stdout = sys.stdout.getvalue()
            ok_("myapp [--core-opts]" in stdout)
            ok_("/usr/local/bin" not in stdout)

        @trap
        def uses_overridden_value_when_given(self):
            Program(binary='nope').run("myapp --help", exit=False)
            ok_("nope [--core-opts]" in sys.stdout.getvalue())

    class initial_context:
        def _names(self, program):
            return program.initial_context().args.keys()

        def contains_truly_core_arguments_regardless_of_namespace_value(self):
            # Spot check. See integration-style --help tests for full argument
            # checkup.
            for program in (Program(), Program(namespace=Collection())):
                names = self._names(program)
                for arg in ('complete', 'debug', 'warn-only'):
                    ok_(arg in names, "{0} not in {1}".format(arg, names))

        def null_namespace_triggers_task_related_args(self):
            p = Program(namespace=None)
            names = self._names(p)
            for arg in p.task_args:
                name = arg.name
                ok_(name in names, "{0} not in {1}".format(name, names))

        def non_null_namespace_does_not_trigger_task_related_args(self):
            p = Program(namespace=Collection())
            names = self._names(p)
            for arg in p.task_args:
                name = arg.name
                ok_(name not in names, "{0} in {1}".format(name, names))

        # TODO: integration tests

    class run:
        class bundled_namespace:
            class when_None:
                def seeks_and_loads_tasks_module(self):
                    skip()

            class when_Collection:
                def does_not_seek(self):
                    skip()
