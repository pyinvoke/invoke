from invoke import task, run


@task
def foo():
    print("Yup")
