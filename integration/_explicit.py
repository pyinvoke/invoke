from invoke import task


@task
def foo(c: object) -> None:
    """
    Frobazz
    """
    print("Yup")
