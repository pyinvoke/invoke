===================================
Frequently asked/answered questions
===================================


Defining/executing tasks
========================

.. _bad-first-arg:

My task's first/only argument isn't showing up in ``--help``!
-------------------------------------------------------------

Make sure your task isn't :doc:`contextualized </concepts/context>`
unexpectedly! Put another way, this problem pops up if you're using `@ctask
<.ctask>` and forget to define an initial context argument for your task.

For example, can you spot the problem in this sample task file?

::

    from invoke import ctask as task

    @task
    def build(ctx, where, clean=False):
        pass

    @task
    def clean(what):
        pass

This task file doesn't cause obvious errors when sanity-checking it with ``inv
--list`` or ``inv --help``. However, ``clean`` forgot to set aside its first
argument for the context - so Invoke is treating ``what`` as the context
argument! This means it doesn't show up in help output or other command-line
parsing stages.


The command line says my task's first/only argument is invalid!
---------------------------------------------------------------

See :ref:`bad-first-arg` - it's probably the same issue.
