"PyPI/etc distribution artifacts."

from invoke import task, Collection


@task(name="all", default=True)
def all_(c):
    "Build all Python packages."
    pass


@task
def sdist(c):
    "Build classic style tar.gz."
    pass


@task
def wheel(c):
    "Build a wheel."
    pass
