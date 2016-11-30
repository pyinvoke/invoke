from spec import eq_

from invoke import task


@task
def mytask(c):
    eq_(c.hooray, 'yaml')
