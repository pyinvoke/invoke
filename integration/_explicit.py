from invoke import Context, task


@task
def foo(c: Context) -> None:
    """
    Frobazz
    """
    print("Yup")
