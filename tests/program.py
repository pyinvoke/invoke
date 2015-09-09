from mock import patch, Mock
from spec import Spec, eq_, ok_, raises, skip

from invoke import Program

from _utils import load


class Program_(Spec):
    class init:
        "__init__"

        @raises(TypeError)
        def requires_version(self):
            Program()

        def only_version_is_required(self):
            eq_(Program(version='1').version, '1')

        def may_specify_namespace(self):
            foo = load('foo')
            ok_(Program(version='1', namespace=foo).namespace is foo)

        def may_specify_name(self):
            eq_(Program(version='1', name='Myapp').name, 'Myapp')

        def may_specify_binary(self):
            eq_(Program(version='1', binary='myapp').binary, 'myapp')

        def may_inject_parser_class(self):
            c = object
            eq_(Program(version='1', parser_class=c).parser_class, c)

        def may_inject_executor_class(self):
            c = object
            eq_(Program(version='1', executor_class=c).executor_class, c)

    class run:
        class argv:
            @patch('invoke.program.sys')
            def defaults_to_sys_argv(self, mock_sys):
                fake_argv = ['not', 'real']
                mock_sys.argv = fake_argv
                parser = Mock()
                Program(version='1', parser_class=parser).run()
                # Expect that parser.parse_argv() was given sys.argv
                parser.return_value.parse_argv.assert_called_with(fake_argv)

            def uses_a_list_unaltered(self):
                # same as above, how do we know for sure lol
                skip()

            def splits_a_string(self):
                # yup
                skip()

        class namespace_behavior:
            def setup(self):
                # TODO: probably define these within cli.py, then just iterate
                # in the test. Prevents accidentally adding more of them later
                # and forgetting to update tests.
                self.task_args = (
                    '--list',
                    '--collection',
                    '--no-dedupe',
                    '--root',
                )

            class when_None:
                def seeks_and_loads_tasks_module(self):
                    skip()

                def exposes_task_arguments(self):
                    skip()

            class when_Collection:
                def does_not_seek(self):
                    skip()

                def hides_task_arguments(self):
                    skip()

        class name:
            def defaults_to_capitalized_argv_when_None(self):
                skip()

            def may_be_overridden(self):
                skip()

        class binary:
            def defaults_to_argv_when_None(self):
                skip()

            def may_be_overridden(self):
                skip()
