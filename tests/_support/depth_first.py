from invoke import task


@task
def clean_html():
    print("Cleaning HTML")

@task
def clean_tgz():
    print("Cleaning .tar.gz files")

@task(clean_html, clean_tgz)
def clean():
    print("Cleaned everything")

@task
def makedirs():
    print("Making directories")

@task(clean, makedirs)
def build():
    print("Building")

@task
def pretest():
    print("Preparing for testing")

@task(pretest)
def test():
    print("Testing")

@task(build, post=[test])
def deploy():
    print("Deploying")
