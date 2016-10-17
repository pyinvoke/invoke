==============================
Testing Invoke-using codebases
==============================

A handful of tips for testing Invoke codebases, both those that are heavily CLI
oriented, and those that store most of their logic in standalone modules:

Avoid mocking dependency code paths
===================================

For example, instead of long, complex task functions that make liberal use of
`.Context` methods, consolidate logic in subroutines or classes whose input
parameters are more specific to your own code.

This leaves the tasks themselves as "glue" which obtains data from outside your
program & turns it into basic Python primitives handed to your logic functions.

Then, testing your core logic only involves mocking out those basic primitives,
instead of mocking `.Context` or `.Result`.

For example, instead of combining task and logic in one file, passing contexts
around::

    from invoke import task
    from datetime import datetime, timedelta

    @task
    def update_changelog(c):
        if should_update_changelog(c):
            c.run("$EDITOR docs/changelog.rst")

    def should_update_changelog(c):
        secs = c.run("stat -c '%Y' docs/changelog.rst").stdout.strip()
        modified = datetime.fromtimestamp(int(secs))
        delta = datetime.now() - modified
        return delta > timedelta(hours=1)

You could pull most of the logic into its own, more easily tested,
file/function::

    from datetime import datetime, timedelta

    def should_update_changelog(secs):
        modified = datetime.fromtimestamp(int(secs))
        delta = datetime.now() - modified
        return delta > timedelta(hours=1)

Leaving the actual task as follows::

    from invoke import task
    from mymodule import should_update_changelog

    @task
    def update_changelog(c):
        secs = c.run("stat -c '%Y' docs/changelog.rst").stdout.strip()
        if should_update_changelog(secs):
            c.run("$EDITOR docs/changelog.rst")


Expect `Results <.Result>`
==========================

The core Invoke subprocess methods like `~.Context.run` all return `.Result`
objects - which can be readily instantiated by themselves with only partial
data (e.g. standard output, but no exit code or standard error). Leverage this
by writing functions or methods that accept `.Result`; then testing them is as
simple as generating mock results - no real subprocesses necessary.

Use `.MockContext`
==================

When the above approaches aren't feasible or desirable, and your primary
codebases revolve heavily around actual `.Context` objects and their methods
(e.g. being simple tasks with no further abstraction/refactoring applied) -
leverage the public test helper class `.MockContext`.

`.MockContext` simplifies the typical
mock approach (found with libraries like `mock
<https://pypi.python.org/pypi/mock>`_), allowing you to instantiate it with
pre-generated return values for its methods.

Subclass & modify Invoke 'internals'
====================================


