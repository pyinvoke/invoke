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
    def hello():
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
    def clean():
        print("Cleaning")

    @task
    def publish():
        print("Publishing")

    @task(pre=[clean], post=[publish])
    def build():
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
    def clean():
        print("Cleaning")

    @task(clean)
    def build():
        print("Building")

As before, ``invoke build`` would cause ``clean`` to run, then ``build``.

Recursive/chained pre/post-tasks
--------------------------------

Pre-tasks of pre-tasks will also be invoked (as will post-tasks of pre-tasks,
pre-tasks of post-tasks, etc) in a depth-first manner, recursively. Here's a
more complex (if slightly contrived) tasks file::

    @task
    def clean_html():
        print("Cleaning HTML")

    @task
    def clean_tgz():
        print("Cleaning .tar.gz files")

    @task(clean_html, clean_tgz)
    def clean():
        print("Cleaned everything")

    @task
    def makedirs():
        print("Making directories")

    @task(clean, makedirs)
    def build():
        print("Building")

    @task(build)
    def deploy():
        print("Deploying")

With a depth-first behavior, the below is hopefully intuitive to most users::

    $ inv deploy
    Cleaning HTML
    Cleaning .tar.gz files
    Cleaned everything
    Making directories
    Building
    Deploying

        
Parameterizing pre/post-tasks
-----------------------------

By default, pre- and post-tasks are executed with no arguments, even if the
task triggering their execution was given some. When this is not suitable, you
can wrap the task objects with `~.tasks.call` objects which allow you to
specify a call signature::

    @task
    def clean(which=None):
        which = which or 'pyc'
        print("Cleaning {0}".format(which))

    @task(pre=[call(clean, which='all')]) # or call(clean, 'all')
    def build():
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
    def clean():
        print("Cleaning")

    @task(clean)
    def build():
        print("Building")

    @task(build)
    def package():
        print("Packaging")

With deduplication turned off (see below), the above would execute ``clean`` ->
``build`` -> ``build`` again -> ``package``. With duplication, the double
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
``--no-dedupe`` core option. While it doesn't make a ton of real-world sense,
let's imagine we wanted to apply ``--no-dedupe`` to the above example; we'd see
the following output::

    $ invoke --no-dedupe build package
    Cleaning
    Building
    Building
    Packaging

The build step is now running twice.


Parameterizing tasks
====================

The previous example had a bit of duplication in how it was invoked; an
intermediate use case is to bundle up that sort of parameterization into a
"meta" task that itself invokes other tasks in a parameterized fashion.

TK: API for this? at CLI level would have to be unorthodox invocation, e.g.::

    @task
    def foo(bar):
        print(bar)

    $ invoke --parameterize foo --param bar --values 1 2 3 4
    1
    2
    3
    4

Note how there's no "real" invocation of ``foo`` in the normal sense. How to
handle partial application (e.g. runtime selection of other non-parameterized
arguments)? E.g.::

    @task
    def foo(bar, biz):
        print("%s %s" % (bar, biz))

    $ invoke --parameterize foo --param bar --values 1 2 3 4 --biz "And a"
    And a 1
    And a 2
    And a 3
    And a 4

That's pretty clunky and foregoes any multi-task invocation. But how could we
handle multiple tasks here? If we gave each individual task flags for this,
like so::

    $ invoke foo --biz "And a" --param foo --values 1 2 3 4

We could do multiple tasks, but then we're stomping on tasks' argument
namespaces (we've taken over ``param`` and ``values``). Really hate that.

**IDEALLY** we'd still limit parameterization to library use since it's an
advanced-ish feature and frequently the parameterization vector is dynamic (aka
not the sort of thing you'd give at CLI anyway)

Probably best to leave that in the intermediate docs and keep it lib level;
it's mostly there for Fabric and advanced users, not something the average
Invoke-only user would care about. Not worth the effort to make it work on CLI
at this point.

::

    @task
    def stuff(var):
        print(var)

    # NOTE: may need to be part of base executor since Collection has to know
    # to pass the parameterization option/values into Executor().execute()?
    class ParameterizedExecutor(Executor):
        # NOTE: assumes single dimension of parameterization.
        # Realistically would want e.g. {'name': [values], ...} structure and
        # then do cross product or something
        def execute(self, task, args, kwargs, parameter=None, values=None):
            # Would be nice to generalize this?
            if parameter:
                # TODO: handle non-None parameter w/ None values (error)
                # NOTE: this is where parallelization would occur; probably
                # need to move into sub-method
                for value in values:
                    my_kwargs = dict(kwargs)
                    my_kwargs[parameter] = value
                    super(self, ParameterizedExecutor).execute(task, kwargs=my_kwargs)
            else:
                super(self, ParameterizedExecutor).execute(task, args, kwargs)


Getting hairy: one task, with one pre-task, parameterized
=========================================================

::

    @task
    def setup():
        print("Yay")

    @task(pre=[setup])
    def build():
        print("Woo")

    class OhGodExecutor(Executor):
        def execute(self, task, args, kwargs, parameter, values):
            # assume always parameterized meh
            # Run pretasks once only, instead of once per parameter value
            for pre in task.pre:
                self.execute(self.collection[pre])
            for value in values:
                my_kwargs = dict(kwargs)
                my_kwargs[parameter] = value
                super(self, OhGodExecutor).execute(task, kwargs=my_kwargs)


Still hairy: one task, with a pre-task that itself has a pre-task
=================================================================

All the things: two tasks, each with pre-tasks, both parameterized
==================================================================
