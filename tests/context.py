from spec import Spec, skip, eq_, ok_

from invoke.context import Context
from invoke.config import Config


class Context_(Spec):
    class init:
        "__init__"
        def takes_optional_config_arg(self):
            # Meh-tastic doesn't-barf tests. MEH.
            Context()
            Context(config={'foo': 'bar'})

    class methods_exposed:
        def _expect_attr(self, attr):
            c = Context()
            ok_(hasattr(c, attr) and callable(getattr(c, attr)))

        # NOTE: actual behavior of command running is tested in runners.py
        def run(self):
            self._expect_attr('run')

        def sudo(self):
            self._expect_attr('sudo')

        # TODO: how exactly to test sudo given it is just going to tie together
        # two other things? Probably just literal "it wraps in a sudo command
        # and sets a sudo response" things?
        # TODO: where should its code LIVE exactly? It's not a runner subclass;
        # so should it literally live here in Context? Not sure where else it
        # could.
        # TODO: do we expose a global function like we do with run() too? Feels
        # like "no, it's not nearly as globally useful for the 'better
        # subprocess wrapper' use case"?

    class configuration_proxy:
        "Dict-like proxy for self.config"
        def setup(self):
            config = Config({'foo': 'bar'})
            self.c = Context(config=config)

        def direct_access_allowed(self):
            eq_(self.c.config.__class__, Config)
            eq_(self.c.config['foo'], 'bar')
            eq_(self.c.config.foo, 'bar')

        def getitem(self):
            "___getitem__"
            eq_(self.c['foo'], 'bar')

        def getattr(self):
            "__getattr__"
            eq_(self.c.foo, 'bar')

        def get(self):
            eq_(self.c.get('foo'), 'bar')
            eq_(self.c.get('biz', 'baz'), 'baz')

        def keys(self):
            skip()

        def values(self):
            skip()

        def iter(self):
            "__iter__"
            skip()

        def update(self):
            self.c.update({'newkey': 'newval'})
            eq_(self.c['newkey'], 'newval')
