from spec import eq_

from invoke import task, Collection


@task
def mytask(c):
    eq_(c.hooray, 'yaml')


ns = Collection(mytask)
