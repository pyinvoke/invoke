from spec import Spec, eq_

from invoke import Context


class Context_(Spec):
    class sudo:
        def base_case(self):
            # TODO: create passworded sudo user
            config = {'sudo': {'password': ''}}
            result = Context(config=config).sudo('whoami')
            eq_(result.stdout.strip(), 'root')
