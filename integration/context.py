from spec import Spec, eq_

from invoke import Context, Config


class Context_(Spec):
    class sudo:
        def base_case(self):
            # TODO: create passworded sudo user
            config = Config(overrides={'sudo': {'password': ''}})
            result = Context(config=config).sudo('whoami', hide=True)
            eq_(result.stdout.strip(), 'root')
