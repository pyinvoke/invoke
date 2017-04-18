==========================
Frequently asked questions
==========================


General project questions
=========================

.. _invoke-split-from-fabric:

Why was Invoke split off from the `Fabric <http://fabfile.org>`_ project?
-------------------------------------------------------------------------

Fabric (1.x and earlier) was a hybrid project implementing two feature sets:
task execution (organization of task functions, execution of them via CLI, and
local shell commands) and high level SSH actions (organization of
servers/hosts, remote shell commands, and file transfer).

For use cases requiring both feature sets, this arrangement worked well.
However, over time it became clear many users only needed one or the other,
with local-only users resenting heavy SSH/crypto install requirements, and
remote-focused users struggling with API limitations caused by the hybrid
codebase.

When planning Fabric 2.x, having the "local" feature set as a standalone
library made sense, and it seemed plausible to design the SSH component as a
separate layer above. Thus, Invoke was created to focus exclusively on local
and abstract concerns, leaving Fabric 2.x concerned only with servers and
network commands.

Fabric 2 leverages many parts of Invoke's API, and allows (but does not
require!) use of Invoke's CLI features, allowing multiple use cases (build
tool, high level SSH lib, hybrid build/orchestration tool) to coexist without
negatively impacting each other.


Defining/executing tasks
========================

.. _bad-first-arg:

My task's first argument isn't showing up in ``--help``!
--------------------------------------------------------

This problem pops up if you forget to define an initial context argument for
your task.

For example, can you spot the problem in this sample task file?

::

    from invoke import task

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
`~invoke.run` nothing appears to happen at first, and then all the output
prints once it's done executing.

This is usually due to Python - the "inner" Python executable you're invoking,
not the one Invoke is running under - performing unwanted buffering of its
output streams. It does this when it thinks it's being called in a
non-interactive fashion.

The fix is simple - force Invoke to run the command in a pseudoterminal by
saying ``pty=True`` (e.g. ``run("python foo", pty=True)``).

Alternately, since both Invoke and the inner command are Python, you could try
loading the inner Python module directly in your Invoke-using code, and call
whichever methods its command-line stub is using - instead of using
`~invoke.run`. This can often have other benefits too.

.. _program-behavior-ptys:

Why is my command behaving differently under Invoke versus being run by hand?
-----------------------------------------------------------------------------

99% of the time, adding ``pty=True`` to your ``run`` call will make things work
as you were expecting. Read on for why this is (and why ``pty=True`` is not the
default).

Command-line programs often change behavior depending on whether a controlling
terminal is present; a common example is the use or disuse of colored output.
When the recipient of your output is a human at a terminal, you may want to use
color, tailor line length to match terminal width, etc.

Conversely, when your output is being sent to another program (shell pipe, CI
server, file, etc) color escape codes and other terminal-specific behaviors can
result in unwanted garbage.

Invoke's use cases span both of the above - sometimes you only want data
displayed directly, sometimes you only want to capture it as a string; often
you want both. Because of this, there is no "correct" default behavior re: use
of a pseudo-terminal - some large chunk of use cases will be inconvenienced
either way.

For use cases which don't care, direct invocation without a pseudo-terminal is
faster & cleaner, so it is the default.

.. _stdin-not-tty:

Why do I sometimes see ``err: stdin: is not a tty``?
----------------------------------------------------

See :ref:`program-behavior-ptys` - the same root cause (lack of a PTY by
default) is probably what's going on. In some cases (such as via the Fabric
library) it's happening because a shell's login files are calling programs that
require a PTY (e.g. ``biff`` or ``mesg``) so make sure to look there if the
actual foreground command doesn't seem at fault.

Everything just exits silently after I run a command!
-----------------------------------------------------

Double check the command's exit code! By default, receiving nonzero exit codes
at the end of a `~invoke.run` call will result in Invoke halting execution &
exiting with that same code. Some programs (pylint, Nagios check scripts,
etc) use exit codes to indicate non-fatal status, which can be confusing.

The solution here is simple: add ``warn=True`` to your `~invoke.run` call,
which disables the automatic exit behavior. Then you can check the result's
``.exited`` attribute by hand to determine if it truly succeeded.


The auto-responder functionality isn't working for my password prompts!
-----------------------------------------------------------------------

Some programs write password prompts or other output *directly* to the local
terminal (the operating-system-level TTY device), bypassing the usual
stdout/stderr streams. For example, this is exactly what `the stdlib's getpass
module <getpass.getpass>` does, if you're calling a program that happens to be
written in Python.

When this happens, we're powerless, because all we get to see is the
subprocess' regular output streams. Thankfully, the solution is usually easy:
just add ``pty=True`` to your `~invoke.run` call. Forcing use of an explicit
pseudo-terminal usually tricks these kinds of programs into writing prompts to
stderr.


I'm getting ``IOError: Inappropriate ioctl for device`` when I run commands!
----------------------------------------------------------------------------

This error typically means some code in your project or its dependencies has
replaced one of the process streams (``sys.stdin``, ``sys.stdout`` or
``sys.stderr``) with an object that isn't actually hooked up to a terminal, but
which pretends that it is. For example, test runners or build systems often do
this.

Technically, what's happened is that the object handed to Invoke's command
executor as e.g. ``run('command', in_stream=xxx)`` (or ``out_stream`` or etc;
and these all default to the ``sys`` members listed above) implements a
``fileno`` method that is not returning the ID of a real terminal file
descriptor. Breaking the contract in this way is what's leading Invoke to do
things the OS doesn't like.

We're always trying to make this detection smarter; if upgrading to the latest
version of Invoke doesn't fix the problem for you, please submit a bug report
including details about the values and types of ``sys.stdin/stdout/stderr``.
Hopefully we'll find another heuristic we can use!
