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


Pre-tasks
=========

Tasks may specify that other tasks should always run before they themselves
run, by giving task objects as non-keyword arguments to ``@task`` (or
explicitly via the ``pre`` keyword argument). Example::

    @task
    def clean():
        print("Cleaning")

    @task(clean) # or @task(pre=[clean])
    def build():
        print("Building")

Execution::

    $ invoke build
    Cleaning
    Building
        
Parameterizing pre-tasks
------------------------

By default, pre-tasks are executed with no arguments. When this is not
suitable, you can replace the task objects with calls to `~.tasks.call`, which
takes a task name and a call signature::

    @task
    def clean(which=None):
        which = which or 'pyc'
        print("Cleaning {0}".format(which))

    @task(pre=[call(clean, which='all')]) # or just call(clean, 'all')
    def build():
        print("Building")

Example output::

    $ invoke build
    Cleaning all
    Building


Task deduplication
==================

By default, any task that would get run multiple times during a session due to
inclusion in ``pre``/``post`` hooks, will only run the first time it is
encountered. Example::

    @task
    def clean():
        print("Cleaning")

    @task(clean)
    def build():
        print("Building")

    @task(pre=[build])
    def package():
        print("Packaging")

Execution::

    $ invoke build package
    Cleaning
    Building
    Packaging

We invoked ``build`` and ``package``; ``package`` itself depends on ``build``;
but we still only ran ``build`` once.

Tasks mentioned on the CLI multiple times will always run that many times, so
e.g.::

    $ invoke build build

would run ``build`` two times (though ``clean`` would still only run once).

.. note::
    Parameterized pre-tasks (using `~.tasks.call`) are deduped based on their
    argument lists, so if our ``clean()`` above took a parameter, ``call(clean,
    'all')`` and ``call(clean, 'html')`` would not be deduped, but two
    instances of ``call(clean, 'all')`` would.

Foregoing deduplication of tasks
================================

If you prefer your tasks to run every time, regardless of how often they appear
in ``pre`` or ``post`` options (or on the command line), you can give the
``--no-dedupe`` core option. While it doesn't make a ton of real-world sense,
let's imagine we wanted to apply ``--no-dedupe`` to the above example::

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
