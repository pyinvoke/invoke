from invoke.task import task

@task
def mytask():
    pass

print mytask
print mytask.is_invoke_task
