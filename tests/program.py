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
            eq_(Program(version='0.1.0').version, '0.1.0')

        def may_specify_namespace(self):
            foo = load('foo')
            ok_(Program(version='0.1.0', namespace=foo).namespace is foo)

    class run:
        class argv:
            def defaults_to_sys_argv(self):
                # mock sys.argv lol
                # ensure that whatever run does, sees our mock
                skip()

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
