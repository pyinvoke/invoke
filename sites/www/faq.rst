==========================
Frequently asked questions
==========================


Defining/executing tasks
========================

.. _bad-first-arg:

My task's first argument isn't showing up in ``--help``!
--------------------------------------------------------

Make sure your task isn't :ref:`contextualized <concepts-context>`
unexpectedly! Put another way, this problem pops up if you're using `@ctask
<invoke.tasks.ctask>` and forget to define an initial context argument for
your task.

For example, can you spot the problem in this sample task file?

::

    from invoke import ctask as task

    @task
    def build(ctx, where, clean=False):
        pass

    @task
    def clean(what):
        pass

This task file doesn't cause obvious errors when sanity-checking it with
``inv --list`` or ``inv --help``. However, ``clean`` forgot to set aside its
first argument for the context - so Invoke is treating ``what`` as the context
argument! This means it doesn't show up in help output or other command-line
parsing stages.


The command line says my task's first argument is invalid!
----------------------------------------------------------

See :ref:`bad-first-arg` - it's probably the same issue.



Running local shell commands (``run``)
======================================

Calling Python or Python scripts prints all the output at the end of the run!
-----------------------------------------------------------------------------

.. note::
    This is typically a problem under Python 3 only.

The symptom is easy to spot - you're running a command that takes a few seconds
or more to execute, it usually prints lines of text as it goes, but via
`~invoke.runner.run` nothing appears to happen at first, and then all the
output prints once it's done executing.

This is usually due to Python - the "inner" Python executable you're invoking,
not the one Invoke is running under - performing unwanted buffering of its
output streams. It does this when it thinks it's being called in a
non-interactive fashion.

The fix is simple - force Invoke to run the command in a pseudoterminal by
saying ``pty=True`` (e.g. ``run("python foo", pty=True)``).

Alternately, since both Invoke and the inner command are Python, you could try
loading the inner Python module directly in your Invoke-using code, and call
whichever methods its command-line stub is using - instead of using
`~invoke.runner.run`. This can often have other benefits too.
