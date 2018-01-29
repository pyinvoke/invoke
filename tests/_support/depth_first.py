from invoke import task


@task
def clean_html(ctx):
    print("Cleaning HTML")

@task
def clean_tgz(ctx):
    print("Cleaning .tar.gz files")

@task(clean_html, clean_tgz)
def clean(ctx):
    print("Cleaned everything")

@task
def makedirs(ctx):
    print("Making directories")

@task(clean, makedirs)
def build(ctx):
    print("Building")

@task
def pretest(ctx):
    print("Preparing for testing")

@task(pretest)
def test(ctx):
    print("Testing")

@task(build, post=[test])
def deploy(ctx):
    print("Deploying")
