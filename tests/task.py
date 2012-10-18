from spec import Spec, skip, eq_, raises

from invoke.task import task
from invoke.loader import Loader

from _utils import support


class _Dummy(object):
    pass


class task_(Spec):
    "@task"

    def setup(self):
        self.loader = Loader(root=support)
        self.vanilla = self.loader.load_collection('decorator')

    def allows_access_to_wrapped_object(self):
        dummy = _Dummy()
        eq_(task(dummy).body, dummy)

    def allows_alias_specification(self):
        eq_(self.vanilla['foo'], self.vanilla['bar'])

    def allows_default_specification(self):
        eq_(self.vanilla[''], self.vanilla['biz'])

    @raises(ValueError)
    def raises_ValueError_on_multiple_defaults(self):
        self.loader.load_collection('decorator_multi_default')

    def allows_annotating_args_as_positional(self):
        eq_(self.vanilla['one_positional'].positional, ('pos',))
        eq_(self.vanilla['two_positionals'].positional, ('pos1', 'pos2'))


class Task_(Spec):
    class get_arguments:
        def setup(self):
            @task(positional=['arg3', 'arg1'])
            def mytask(arg1, arg2=False, arg3=5):
                pass
            self.task = mytask
            self.args = self.task.get_arguments()

        def positional_args_come_first(self):
            eq_(self.args[0].name, 'arg3')
            eq_(self.args[1].name, 'arg1')
            eq_(self.args[2].name, 'arg2')

        def kinds_are_preserved(self):
            eq_(
                map(lambda x: x.kind, self.args),
                # Remember that the default 'kind' is a string.
                [int, str, bool]
            )

        def positional_flag_is_preserved(self):
            eq_(
                map(lambda x: x.positional, self.args),
                [True, True, False]
            )
