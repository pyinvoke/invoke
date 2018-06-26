from invoke import task, Collection

from . import build, deploy, provision


@task(aliases=["ipython"])
def shell(c):
    "Load a REPL with project state already set up."
    pass


@task(aliases=["run_tests"], default=True)
def test(c):
    "Run the test suite with baked-in args."
    pass


# NOTE: using build's internal collection directly as a way of ensuring a
# corner case (collection 'named' via local kwarg) gets tested for --list.
# NOTE: Docstring cloning in effect to preserve the final organic looking
# result...
localbuild = build.ns
localbuild.__doc__ = build.__doc__
ns = Collection(shell, test, deploy, provision, build=localbuild)
