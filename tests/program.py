from mock import patch, Mock
from spec import Spec, eq_, ok_, raises, skip

from invoke import Program, Collection

from _utils import load


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

        def may_inject_parser_class(self):
            c = object
            eq_(Program(parser_class=c).parser_class, c)

        def may_inject_executor_class(self):
            c = object
            eq_(Program(executor_class=c).executor_class, c)

    class normalize_argv:
        @patch('invoke.program.sys')
        def defaults_to_sys_argv(self, mock_sys):
            fake_argv = ['not', 'real']
            mock_sys.argv = fake_argv
            eq_(Program().normalize_argv(None), fake_argv)

        def uses_a_list_unaltered(self):
            eq_(Program().normalize_argv(['foo', 'bar']), ['foo', 'bar'])

        def splits_a_string(self):
            eq_(Program().normalize_argv("foo bar"), ['foo', 'bar'])

    class get_name:
        def defaults_to_capitalized_argv_when_None(self):
            eq_(Program().get_name(['program', 'args']), 'Program')

        def uses_overridden_value_when_given(self):
            eq_(
                Program(name='NotProgram').get_name(['program', 'args']),
                'NotProgram'
            )

        # TODO: integration test for one or both

    class get_binary:
        def defaults_to_argv_when_None(self):
            eq_(Program().get_binary(['program', 'args']), 'program')

        def uses_overridden_value_when_given(self):
            eq_(
                Program(binary='nope').get_binary(['program', 'args']),
                'nope'
            )

        # TODO: integration test for one or both

    class initial_context:
        def setup(self):
            # TODO: probably define these within cli.py, then just iterate
            # in the test. Prevents accidentally adding more of them later
            # and forgetting to update tests.
            self.task_args = (
                '--list',
                '--collection',
                '--no-dedupe',
                '--root'
            )

        def _names(self, program):
            return program.initial_context().flag_names()

        def contains_truly_core_arguments_regardless_of_namespace_value(self):
            # Spot check. See integration-style --help tests for full argument
            # checkup. TODO: maybe make this programmatic like the above TODO.
            for program in (Program(), Program(namespace=Collection())):
                names = self._names(program)
                for arg in ('--complete', '--debug', '--warn-only'):
                    ok_(arg in names, "{0} not in {1}".format(arg, names))

        def null_namespace_triggers_task_related_args(self):
            names = self._names(Program(namespace=None))
            for arg in self.task_args:
                ok_(arg in names, "{0} not in {1}".format(arg, names))

        def non_null_namespace_does_not_trigger_task_related_args(self):
            names = self._names(Program(namespace=Collection()))
            for arg in self.task_args:
                ok_(arg not in names, "{0} in {1}".format(arg, names))

    class run:
        @raises(TypeError)
        def requires_argv(self):
            Program().run()

        class namespace_behavior:
            class when_None:
                def seeks_and_loads_tasks_module(self):
                    skip()

            class when_Collection:
                def does_not_seek(self):
                    skip()
