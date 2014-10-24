from spec import eq_

from invoke import ctask


@ctask
def mytask(c):
    print "wat"
    eq_(c.hooray, 'yaml')
