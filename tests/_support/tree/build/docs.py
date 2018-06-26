"Tasks for managing Sphinx docs."

from invoke import task, Collection


@task(name="all", default=True)
def all_(c):
    "Build all doc formats."
    pass


@task
def html(c):
    "Build HTML output only."
    pass


@task
def pdf(c):
    "Build PDF output only."
    pass
