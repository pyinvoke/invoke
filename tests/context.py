from spec import Spec
from mock import patch

from invoke.context import Context


class Context_(Spec):
    class run_:
        @patch('invoke.context.run')
        def honors_warn_state(self, run):
            Context(run={'warn': False}).run('x')
            run.assert_called_with('x', warn=False)
