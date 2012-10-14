from invoke.task import task
from invoke.run import run


@task
def test(module=None):
    base = "spec"
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else "")
    # Use pty so the spec/nose/Python process buffers "correctly"
    run(base + args, pty=True)
