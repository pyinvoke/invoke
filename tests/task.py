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
