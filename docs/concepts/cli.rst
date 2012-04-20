==============
CLI invocation
==============

Introduction
============

Invoke's command line invocation utilizes traditional style command-line flags
and task name arguments, subject to the following rules:

* Core options modifying Invoke's own behavior must come first, before any task
  names.
* Task names are specified as simple string arguments.
* Tasks may be parameterized by specifying flags following the task name.
* Multiple tasks may be given (in the order to be executed).

Some examples will make this clear.


Basic invocation & core options
===============================

The most basic form is just Invoke by
itself, which behaves the same as ``-h``/``--help``::

    $ invoke
    Usage: invoke [core options] [task [task-options], ...]
    ...

 Core options with no tasks can either cause administrative actions, like
 listing available tasks::

    $ invoke --list
    Available tasks:

        foo
        bar
        ...

Or they can modify behavior, such as overriding the default task collections
searched for::

    $ invoke --collection mytasks --list
    Available tasks:

        mytask
        ...


Tasks and task options
======================

The simplest task invocation, for a task requiring no parameterization::

    $ invoke mytask

Tasks may take parameters in the form of flag arguments::

    $ invoke build --format=html
    $ invoke build --format html
    $ invoke build -f pdf
    $ invoke build -f=pdf

Note that both long and short style flags are supported, and that equals signs
are optional.

Boolean options are simple flags with no arguments, which turn the Python level
values from ``False`` to ``True``::

    $ invoke build --progress-bar


Multiple tasks
==============

More than one task may be given at the same time, and they will be executed in
order. When a new task is encountered, option processing for the previous task
stops, so there is no ambiguity about which option/flag belongs to which task.
For example, this invocation specifies two tasks, ``clean`` and ``build``, both
parameterized::

    $ invoke clean -t all build -f pdf

Another example with no parameterizing::

    $ invoke clean build


Mixing things up
================

Core options are similar to task options, in that they must be specified before any
tasks are given. This invoke says to load the ``mytasks`` collection and call
that collection's ``foo`` task::

    $ invoke --collection mytasks foo --foo-args
