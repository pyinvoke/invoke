from spec import Spec, skip, eq_
from mock import patch

from invoke.context import Context


class Context_(Spec):
    class init:
        "__init__"
        def takes_optional_run_and_config_args(self):
            # Meh-tastic doesn't-barf tests. MEH.
            Context()
            Context(run={'foo': 'bar'})
            Context(config={'foo': 'bar'})

    class run_:
        def _honors(self, kwarg, value):
            with patch('invoke.context.run') as run:
                Context(run={kwarg: value}).run('x')
                run.assert_called_with('x', **{kwarg: value})

        def warn(self):
            self._honors('warn', True)

        def hide(self):
            self._honors('hide', 'both')

        def pty(self):
            self._honors('pty', True)

        def echo(self):
            self._honors('echo', True)

    class run_and_expand:

        def vars_from_context_config(self):
            with patch('invoke.context.run') as run:
                Context(config={'foo': 'bar'}).run('echo $foo', expand=True)
                run.assert_called_with('echo bar')

        def vars_from_run_config(self):
            with patch('invoke.context.run') as run:
                Context().run('echo $foo', expand=True, config={'foo': 'xyz'})
                run.assert_called_with('echo xyz')

        def vars_from_run_config_overrides_context_config(self):
            with patch('invoke.context.run') as run:
                Context(config={'foo': 'bar'}).run(
                    'echo $foo', expand=True, config={'foo': 'xyz'})
                run.assert_called_with('echo xyz')

        def expand_set_on_context(self):
            with patch('invoke.context.run') as run:
                Context(config={'foo': 'bar'}, run={'expand': True}).run(
                    'echo $foo')
                run.assert_called_with('echo bar')

        def var_with_dot(self):
            with patch('invoke.context.run') as run:
                Context(config={'foo.x': 'bar'}).run(
                    'echo $foo.x', expand=True)
                run.assert_called_with('echo bar')

        def var_with_dash(self):
            with patch('invoke.context.run') as run:
                Context(config={'foo-x': 'bar'}).run(
                    'echo $foo-x', expand=True)
                run.assert_called_with('echo bar')

        def var_with_braces(self):
            with patch('invoke.context.run') as run:
                Context(config={'foo': 'bar', 'foox': 'xyz'}).run(
                    'echo ${foo}x', expand=True)
                run.assert_called_with('echo barx')

    class clone:
        def returns_copy_of_self(self):
            skip()

        def contents_of_dicts_are_distinct(self):
            skip()

    class configuration:
        "Dict-like for config"
        def setup(self):
            self.c = Context(config={'foo': 'bar'})

        def getitem(self):
            "___getitem__"
            eq_(self.c['foo'], 'bar')

        def get(self):
            eq_(self.c.get('foo'), 'bar')
            eq_(self.c.get('biz', 'baz'), 'baz')

        def keys(self):
            skip()

        def update(self):
            self.c.update({'newkey': 'newval'})
            eq_(self.c['newkey'], 'newval')
