from spec import eq_

from invoke import ctask, Collection


@ctask
def collection(c):
    c.run('false') # Ensures a kaboom if mocking fails


ns = Collection(collection)
ns.configure({'run': {'echo': True}})
