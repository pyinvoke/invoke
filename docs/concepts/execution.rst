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


Base case: one task, nothing but
================================

::
    @task
    def func():
        print("Hello, world!")

    class Executor(object):
        def __init__(self, collection):
            self.collection = collection

        def execute(self, task, args, kwargs, parameterizations):
            task()

    coll = Collection(func)
    coll.execute('func', Executor)
    # basically is: Executor(<self-the-coll>).execute(self[name], ...)


A bit extra: one task with one pre-task
=======================================

::
    @task
    def setup():
        print("Setting up!")

    @task(pre=['setup'])
    def func():
        print("Hello, world!")

    class PreHonoringExecutor(Executor):
        def execute(self, task):
            for pre in task.pre:
                self.execute(self.collection[pre])
            task()
        

Getting more realistic: two tasks, both prerequiring another
============================================================

And ensuring that any given task only runs once per session!

::
    @task
    def clean():
        print("Cleaning")

    @task(pre=['clean'])
    def setup():
        print("Setting up!")

    @task(pre=['setup', 'clean'])
    def func():
        print("Hello, world!")

    class RunsOnceExecutor(PreHonoringExecutor):
        def execute(self, task):
            if not self.collection.times_run(task.name):
                # Use super() to handle pre-run execution
                super(self, RunsOnceExecutor).execute(task)
                self.collection.note_run(task.name)


Pretty advanced: one task, parameterized
========================================

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
                for value in values:
                    my_kwargs = dict(kwargs)
                    my_kwargs[parameter] = value
                    super(self, Executor).execute(task, kwargs=my_kwargs)
            else:
                super(self, Executor).execute(task, args, kwargs)


Getting hairy: one task, with one pre-task, parameterized
=========================================================

Still hairy: one task, with a pre-task that itself has a pre-task
=================================================================

All the things: two tasks, each with pre-tasks, both parameterized
==================================================================
