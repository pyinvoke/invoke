Invoke is a Python (2.6+ and 3.3+) task execution tool & library, drawing
inspiration from various sources to arrive at a powerful & clean feature set.

* Like Ruby's Rake tool and Invoke's own predecessor Fabric 1.x, it provides a
  clean, high level API for running shell commands and defining/organizing
  task functions from a ``tasks.py`` file:

  .. code-block:: python

    from invoke import task

    @task
    def clean(ctx, docs=False, bytecode=False, extra=''):
        patterns = ['build']
        if docs:
            patterns.append('docs/_build')
        if bytecode:
            patterns.append('**/*.pyc')
        if extra:
            patterns.append(extra)
        for pattern in patterns:
            ctx.run("rm -rf %s" % pattern)

    @task
    def build(ctx, docs=False):
        ctx.run("python setup.py build")
        if docs:
            ctx.run("sphinx-build docs docs/_build")

* From GNU Make, it inherits an emphasis on minimal boilerplate for common
  patterns and the ability to run multiple tasks in a single invocation::

    $ invoke clean build

* Where Fabric 1.x considered the command-line approach the default mode of
  use, Invoke (and tools built on it) are equally at home embedded in your own
  Python code or a REPL::

    >>> from invoke import run
    >>> result = run("pip install -r requirements.txt", hide=True, warn=True)
    >>> print(result.ok)
    True
    >>> print(result.stdout[-1])
    Successfully installed invocations-0.13.0 pep8-1.5.7 spec-1.3.1
    >>>

* Following the lead of most Unix CLI applications, it offers a traditional
  flag-based style of command-line parsing, deriving flag names and value types
  from task signatures (optionally, of course!)::

    $ invoke clean --docs --bytecode build --docs --extra='**/*.pyo'
    $ invoke clean -d -b build --docs -e '**/*.pyo'
    $ invoke clean -db build -de '**/*.pyo'

* Like many of its predecessors, it offers advanced features as well --
  namespacing, task aliasing, before/after hooks, parallel execution and more.

For documentation, including detailed installation information, please see
http://pyinvoke.org. Post-install usage information may be found in ``invoke
--help``.

You can install the development version via ``pip install -e
git+https://github.com/pyinvoke/invoke#egg=invoke``.
