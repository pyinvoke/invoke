from invoke import task


@task
def expect_config(c):
    password = c.config.sudo.password
    assert password == "mypassword", "Got {!r}".format(password)
