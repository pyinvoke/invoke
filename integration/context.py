import os

from spec import Spec, eq_, skip

from invoke import Context, Config


class Context_(Spec):
    class sudo:
        def base_case(self):
            if not os.environ.get('TRAVIS', False):
                skip()
            # NOTE: Assumes 'testuser:mypass' has been created & added to
            # passworded (not passwordless) sudo configuration; and assumes
            # that the user RUNNING the tests DOES have passwordless sudo.
            # I.e., travis-ci.
            config = Config(overrides={'sudo': {'password': 'mypass'}})
            cmd = 'sudo -u testuser sudo whoami'
            result = Context(config=config).sudo(cmd, hide=True)
            eq_(result.stdout.strip(), 'root')
