"System setup code."

from invoke import task, Collection

@task
def db(c):
    "Stand up one or more DB servers."
    pass

@task
def web(c):
    "Stand up a Web server."
    pass
