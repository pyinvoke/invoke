from mock import patch
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

    class sudo:
        @patch('invoke.context.Local')
        def prefixes_command_with_sudo(self, Local):
            runner = Local.return_value
            Context().sudo('whoami')
            # NOTE: implicitly tests default sudo.prompt conf value
            cmd = "sudo -S -p '__autoresponse-sudo-prompt__' whoami"
            ok_(runner.run.called, "sudo() never called run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch('invoke.context.Local')
        def honors_config_for_prompt_value(self, Local):
            runner = Local.return_value
            config = Config(overrides={'sudo': {'prompt': 'FEED ME: '}})
            Context(config=config).sudo('whoami')
            cmd = "sudo -S -p 'FEED ME: ' whoami"
            eq_(runner.run.call_args[0][0], cmd)

        def prompt_value_is_properly_escaped(self):
            # I.e. setting it to "here's johnny!" doesn't explode.
            # NOTE: possibly best to tie into issue #2
            skip()
