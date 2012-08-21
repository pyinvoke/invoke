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

    def sets_arg_help(self):
        eq_(self.vanilla['punch'].helps['why'], 'Motive')

    def sets_arg_kind(self):
        skip()


class Task_(Spec):
    class argspec:
        def setup(self):
            @task
            def mytask(arg1, arg2=False):
                pass
            self.task = mytask

            @task
            def mytask2():
                pass
            self.task2 = mytask2

        def returns_argument_names(self):
            assert 'arg1' in self.task.argspec

        def returns_argument_default_values(self):
            assert self.task.argspec['arg2'] is False

        def works_for_empty_argspecs(self):
            eq_(self.task2.argspec, {})
