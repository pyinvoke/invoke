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
        eq_(self.vanilla.get('foo'), self.vanilla.get('bar'))

    def allows_default_specification(self):
        eq_(self.vanilla.get(), self.vanilla.get('biz'))

    @raises(ValueError)
    def raises_ValueError_on_multiple_defaults(self):
        self.loader.load_collection('decorator_multi_default')


class Task_(Spec):
    class args:
        def setup(self):
            def mytask(arg1, arg2): pass
            self.task = task(mytask)

        def returns_argument_names(self):
            assert 'arg1' in self.task.argspec
