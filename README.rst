.. image:: https://secure.travis-ci.org/pyinvoke/invoke.png?branch=master
        :target: https://travis-ci.org/pyinvoke/invoke

.. image:: https://readthedocs.org/projects/invoke/badge/?version=latest
        :target: https://readthedocs.org/projects/invoke/?badge=latest
        :alt: Documentation Status

Invoke is a Python (2.6+ and 3.2+) task execution tool & library, drawing inspiration from various sources to arrive at a powerful & clean feature set.

* Like Ruby's Rake tool and Invoke's own predecessor Fabric 1.x, it provides a
  clean, high level API for running shell commands and defining/organizing
  task functions from a ``tasks.py`` file::

    from invoke import run, task

    @task
    def clean(docs=False, bytecode=False, extra=''):
        patterns = ['build']
        if docs:
            patterns.append('docs/_build')
        if bytecode:
            patterns.append('**/*.pyc')
        if extra:
            patterns.append(extra)
        for pattern in patterns:
            run("rm -rf %s" % pattern)

    @task
    def build(docs=False):
        run("python setup.py build")
        if docs:
            run("sphinx-build docs docs/_build")

* From GNU Make, it inherits an emphasis on minimal boilerplate for common
  patterns and the ability to run multiple tasks in a single invocation::

    $ invoke clean build

* Following the lead of most Unix CLI applications, it offers a traditional
  flag-based style of command-line parsing, deriving flag names and value types
  from task signatures (optionally, of course!)::

    $ invoke clean --docs --bytecode build --docs --extra='**/*.pyo'
    $ invoke clean -d -b build --docs -e '**/*.pyo'
    $ invoke clean -db build -de '**/*.pyo'

* Like many of its predecessors, it offers advanced features as well --
  namespacing, task aliasing, before/after hooks, parallel execution and more.

For documentation, including detailed installation information, please see
http://docs.pyinvoke.org. Post-install usage information may be found in ``invoke
--help``.

You can install the `development version
<https://github.com/pyinvoke/invoke/tarball/master#egg=invoke-dev>`_ via ``pip
install invoke==dev``.
