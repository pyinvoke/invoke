"How to deploy our code and configs."

from invoke import task


@task(default=True)
def everywhere(c):
    "Deploy to all targets."
    pass


@task(aliases=["db_servers"])
def db(c):
    "Deploy to our database servers."
    pass


@task
def web(c):
    "Update and bounce the webservers."
    pass
