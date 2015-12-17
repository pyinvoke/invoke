import os

from spec import Spec

from invoke import run


class Runner_(Spec):
    class responding:
        def base_case(self):
            # Basic "doesn't explode" test: respond.py will exit nonzero unless
            # this works, causing a Failure.
            os.chdir(os.path.dirname(__file__))
            responses = {r"What's the password\?": "Rosebud\n"}
            # Gotta give -u or Python will line-buffer its stdout, so we'll
            # never actually see the prompt.
            run('python -u _support/respond.py', responses=responses, hide=True)
