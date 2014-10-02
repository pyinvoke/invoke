from spec import eq_

from invoke import ctask


@ctask
def mytask(c):
    eq_(c.project_setting, 'yup')
