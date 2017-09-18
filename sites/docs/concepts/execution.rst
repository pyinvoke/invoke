.. _task-execution:

==============
Task execution
==============

Invoke's task execution mechanisms attempt to bridge the needs of the simple,
base case and advanced use cases involving parameterization, pre/post call
hooks, and so forth. This document lays out the classes and methods involved,
walking you through a couple different scenarios.

Note that this is a generalized walkthrough -- this behavior is the same
regardless of whether the tasks were invoked via the command line, or via
library calls.


Base case
=========

In the simplest case, a task with no pre- or post-tasks runs one time. Example::

    @task
    def hello(ctx):
        print("Hello, world!")

Execution::

    $ invoke hello
    Hello, world!

.. _pre-post-tasks:

Pre- and post-tasks
===================

Tasks that should always have another task executed before or after them, may
use the ``@task`` deocator's ``pre`` and/or ``post`` kwargs, like so::

    @task
    def clean(ctx):
        print("Cleaning")

    @task
    def publish(ctx):
        print("Publishing")

    @task(pre=[clean], post=[publish])
    def build(ctx):
        print("Building")

Execution::

    $ invoke build
    Cleaning
    Building
    Publishing

These keyword arguments always take iterables. As a convenience, pre-tasks (and
pre-tasks only) may be given as positional arguments, in a manner similar to
build systems like ``make``. E.g. we could present part of the above example
as::

    @task
    def clean(ctx):
        print("Cleaning")

    @task(clean)
    def build(ctx):
        print("Building")

As before, ``invoke build`` would cause ``clean`` to run, then ``build``.

Recursive/chained pre/post-tasks
--------------------------------

Pre-tasks of pre-tasks will also be invoked (as will post-tasks of pre-tasks,
pre-tasks of post-tasks, etc) in a depth-first manner, recursively. Here's a
more complex (if slightly contrived) tasks file::

    @task
    def clean_html(ctx):
        print("Cleaning HTML")

    @task
    def clean_tgz(ctx):
        print("Cleaning .tar.gz files")

    @task(clean_html, clean_tgz)
    def clean(ctx):
        print("Cleaned everything")

    @task
    def makedirs(ctx):
        print("Making directories")

    @task(clean, makedirs)
    def build(ctx):
        print("Building")

    @task(build)
    def deploy(ctx):
        print("Deploying")

With a depth-first behavior, the below is hopefully intuitive to most users::

    $ inv deploy
    Cleaning HTML
    Cleaning .tar.gz files
    Cleaned everything
    Making directories
    Building
    Deploying

        
.. _parameterizing-pre-post-tasks:

Parameterizing pre/post-tasks
-----------------------------

By default, pre- and post-tasks are executed with no arguments, even if the
task triggering their execution was given some. When this is not suitable, you
can wrap the task objects with `~.tasks.call` objects which allow you to
specify a call signature::

    @task
    def clean(ctx, which=None):
        which = which or 'pyc'
        print("Cleaning {0}".format(which))

    @task(pre=[call(clean, which='all')]) # or call(clean, 'all')
    def build(ctx):
        print("Building")

Example output::

    $ invoke build
    Cleaning all
    Building


.. _deduping:

Task deduplication
==================

By default, any task that would run more than once during a session (due e.g.
to inclusion in pre/post tasks), will only be run once. Example task file::

    @task
    def clean(ctx):
        print("Cleaning")

    @task(clean)
    def build(ctx):
        print("Building")

    @task(build)
    def package(ctx):
        print("Packaging")

With deduplication turned off (see below), the above would execute ``clean`` ->
``build`` -> ``build`` again -> ``package``. With deduplication, the double
``build`` does not occur::

    $ invoke build package
    Cleaning
    Building
    Packaging

.. note::
    Parameterized pre-tasks (using `~.tasks.call`) are deduped based on their
    argument lists. For example, if ``clean`` was parameterized and hooked up
    as a pre-task in two different ways - e.g. ``call(clean, 'html')`` and
    ``call(clean, 'all')`` - they would not get deduped should both end up
    running in the same session.
    
    However, two separate references to ``call(clean, 'html')`` *would* become
    deduplicated.

Disabling deduplication
-----------------------

If you prefer your tasks to run every time no matter what, you can give the
``--no-dedupe`` core CLI option at runtime, or set the ``tasks.dedupe``
:doc:`config setting </concepts/configuration>` to ``False``. While it
doesn't make a ton of real-world sense, let's imagine we wanted to apply
``--no-dedupe`` to the above example; we'd see the following output::

    $ invoke --no-dedupe build package
    Cleaning
    Building
    Building
    Packaging

The build step is now running twice.
