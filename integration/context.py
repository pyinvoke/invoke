from spec import Spec, eq_

from invoke import Context


class Context_(Spec):
    class sudo:
        def base_case(self):
            # TODO: create passworded sudo user
            result = Context().sudo('whoami')
            eq_(result.stdout.strip(), 'root')
