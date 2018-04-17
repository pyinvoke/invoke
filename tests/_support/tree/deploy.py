"How to deploy our code and configs."

from invoke import task, Collection

@task(default=True)
def everywhere(c):
    "Deploy to all targets."
    pass

@task
def db(c):
    "Deploy to our database servers."
    pass

@task
def web(c):
    "Update and bounce the webservers."
    pass
