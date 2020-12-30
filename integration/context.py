import os

from pytest import skip

from invoke import Context, Config


class Context_:
    class sudo:
        def base_case(self):
            # NOTE: Assumes a user whose password is 'mypass' has been created
            # & added to passworded (not passwordless) sudo configuration; and
            # that this user is the one running the test suite. Only for
            # running on Travis, basically.
            if not os.environ.get("TRAVIS", False):
                skip()
            config = Config({"sudo": {"password": "mypass"}})
            result = Context(config=config).sudo("whoami", hide=True)
            assert result.stdout.strip() == "root"
