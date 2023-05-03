from invoke import task
from . import pytest as pt
import pytest

pytest.__version__


@task
def mytask(c):
    print(pt.hi)
