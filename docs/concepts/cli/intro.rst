=================
Invocation basics
=================

Invoke's command line invocation utilizes traditional style command-line flags
and task name arguments. The most basic form is just Invoke by itself (which
behaves the same as ``-h``/``--help``)::

    $ invoke
    Usage: invoke [core options] [task [task-options], ...]
    ...

    $ invoke -h
    [same as above]

Core options with no tasks can either cause administrative actions, like
listing available tasks::

    $ invoke --list
    Available tasks:

        foo
        bar
        ...

Or they can modify behavior, such as overriding the default task collection
name Invoke looks for::

    $ invoke --collection mytasks --list
    Available tasks:

        mytask1
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
are optional in both cases.

Boolean options are simple flags with no arguments, which turn the Python level
values from ``False`` to ``True``::

    $ invoke build --progress-bar

Naturally, more than one flag may be given at a time::

    $ invoke build --progress-bar -f pdf

Per-task help / printing available flags
----------------------------------------

To get help for a specific task, just give the task name as an argument to the
core ``--help``/``-h`` option::

    $ invoke --help build

    'build' options:
      -f STRING, --format=STRING       Which build format type to use
      --progress-bar, -p               Display progress bar

Globbed short flags
-------------------

Boolean short flags may be combined into one flag expression, so that e.g.::

    $ invoke build -qv

is equivalent to (and expanded into, during parsing)::

    $ invoke build -q -v

If the first flag in a globbed short flag token is not a boolean but takes a
value, the rest of the glob is taken to be the value instead. E.g.::

    $ invoke build -fpdf

is expanded into::

    $ invoke build -f pdf

and **not**::

    $ invoke build -f -p -d -f

Optional flag values
--------------------

You saw a hint of this with ``--help`` specifically, but non-core options may
also take optional values. For example, say your task has a ``--log`` flag
that activates logging::

    $ invoke compile --log

but you also want it to be configurable regarding *where* to log::

    $ invoke compile --log=foo.log

You could implement this with an additional argument (e.g. ``--log`` and
``--log-location``) but sometimes the concise API is the more useful one.

Resolving ambiguity
~~~~~~~~~~~~~~~~~~~

There are a number of situations where ambiguity could arise for a flag that
takes an optional value:

* When a task takes positional arguments and they haven't all been filled in by
  the time the parser arrives at the optional-value flag;
* When the token following one of these flags looks like another flag; or
* When that token has the same name as another task.

In any of these situations, Invoke's parser will `refuse the temptation to
guess <http://www.python.org/dev/peps/pep-0020/>`_ and raise an error.


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
