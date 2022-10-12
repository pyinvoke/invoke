from invoke import task


@task
def expect_config(c):
    password = c.config.sudo.password
    assert password == "mypassword", f"Got {password!r}"
