from invoke import task


@task
def mytask(c) -> None:
    print("hi!")
