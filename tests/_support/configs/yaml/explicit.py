from spec import eq_

from invoke import ctask, Collection


@ctask
def mytask(c):
    eq_(c.hooray, 'yaml')


ns = Collection(mytask)
