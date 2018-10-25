.. _invoking-tasks:

==============
Invoking tasks
==============

This page explains how to invoke your tasks on the CLI, both in terms of parser
mechanics (how your tasks' arguments are exposed as command-line options) and
execution strategies (which tasks actually get run, and in what order).

(For details on Invoke's core flags and options, see :doc:`/invoke`.)

.. contents::
    :local:


.. _basic-cli-layout:

Basic command line layout
=========================

Invoke may be executed as ``invoke`` (or ``inv`` for short) and its command
line layout looks like this::

    $ inv [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

Put plainly, Invoke's `CLI parser <.Parser>` splits your command line up into
multiple "`parser contexts <.ParserContext>`" which allows it to reason about
the args and options it will accept:

- Before any task names are given, the parser is in the "core" parse context,
  and looks for core options and flags such as :option:`--echo`,
  :option:`--list` or :option:`--help`.
- Any non-argument-like token (such as ``mytask``) causes a switch into a
  per-task context (or an error, if no task matching that name seems to exist
  in the :doc:`loaded collection </concepts/loading>`).
- At this point, argument-like tokens are expected to correspond to the
  arguments for the previously named task (see :ref:`task-arguments`).
- Then this cycle repeats infinitely, allowing chained execution of arbitrary
  numbers of tasks. (In practice, most users only execute one or two at a
  time.)

For the core arguments and flags, see :doc:`/invoke`; for details on how your
tasks affect the CLI, read onwards.

.. note::
    There is a minor convenience-minded exception to how parse contexts behave:
    core options *may* also be given inside per-task contexts, *if and only if*
    there is no conflict with similarly-named/prefixed arguments of the
    being-parsed task.

    For example, ``invoke mytask --echo`` will behave identically to ``invoke
    --echo mytask``, *unless* ``mytask`` has its own ``echo`` flag (in which
    case that flag is handed to the task context, as normal).

    Similarly, ``invoke mytask -e`` will turn on command echoing too, unless
    ``mytask`` has its own argument whose shortflag ends up set to ``-e`` (e.g.
    ``def mytask(env)``).


.. _task-arguments:

Task command-line arguments
===========================

The simplest task invocation, for a task requiring no parameterization::

    $ inv mytask

Tasks may take parameters in the form of flag arguments::

    $ inv build --format=html
    $ inv build --format html
    $ inv build -f pdf
    $ inv build -f=pdf

Note that both long and short style flags are supported, and that equals signs
are optional in both cases.

Boolean options are simple flags with no arguments::

    $ inv build --progress-bar

Naturally, more than one flag may be given at a time::

    $ inv build --progress-bar -f pdf

Type casting
------------

Natively, a command-line string is just that -- a string -- requiring some
leaps of logic to arrive at any non-string values on the Python end. Invoke has
a number of these tricks already at hand, and more will be implemented in the
future. Currently:

- Arguments with default values use those default values as a type hint, so
  ``def mytask(c, count=1)`` will see ``inv mytask --count=5`` and result in
  the Python integer value ``5`` instead of the string ``"5"``.

    - Default values of ``None`` are effectively the same as having no default
      value at all - no type casting occurs and you're left with a string.

- The primary exception to the previous rule is booleans: default values of
  ``True`` or ``False`` cause those arguments to show up as actual
  non-value-taking flags (``--argname`` to set the value to ``True`` if the
  default was ``False``, or ``--no-argment`` in the opposite case). See
  :ref:`boolean-flags` for more examples.
- List values (which you wouldn't want to set as an argument's default value
  anyways -- it's a common Python misstep) are served by a special ``@task``
  flag - see :ref:`iterable-flag-values` below.
- There's currently no way to set other compound values (such as dicts) on
  the command-line; solving this more complex problem is left as an exercise to
  the reader (though we may add helpers for such things in the future).

Per-task help / printing available flags
----------------------------------------

To get help for a specific task, you can give the task name as an argument to
the core ``--help``/``-h`` option, or give ``--help``/``-h`` after the task
(which will trigger custom-to-``help`` behavior where the task name itself is
given to ``--help`` as its argument value).

When help is requested, you'll see the task's docstring (if any) and
per-argument/flag help output::

    $ inv --help build  # or invoke build --help

    Docstring:
      none

    Options for 'build':
      -f STRING, --format=STRING  Which build format type to use
      -p, --progress-bar          Display progress bar

Globbed short flags
-------------------

Boolean short flags may be combined into one flag expression, so that e.g.::

    $ inv build -qv

is equivalent to (and expanded into, during parsing)::

    $ inv build -q -v

If the first flag in a globbed short flag token is not a boolean but takes a
value, the rest of the glob is taken to be the value instead. E.g.::

    $ inv build -fpdf

is expanded into::

    $ inv build -f pdf

and **not**::

    $ inv build -f -p -d -f

.. _optional-values:

Optional flag values
--------------------

You saw a hint of this with ``--help`` specifically, but non-core options may
also take optional values, if declared as ``optional``. For example, say your
task has a ``--log`` flag that activates logging::

    $ inv compile --log

but you also want it to be configurable regarding *where* to log::

    $ inv compile --log=foo.log

You could implement this with an additional argument (e.g. ``--log`` and
``--log-location``) but sometimes the concise API is the more useful one.

To enable this, specify which arguments are of this 'hybrid' optional-value
type inside ``@task``::

    @task(optional=['log'])
    def compile(c, log=None):
        if log:
            log_file = '/var/log/my.log'
            # Value was given, vs just-True
            if isinstance(log, unicode):
                log_file = log
            # Replace w/ your actual log setup...
            set_log_destination(log_file)
        # Do things that might log here...

When optional flag values are used, the values seen post-parse follow these
rules:

* If the flag is not given at all (``invoke compile``) the default value
  is filled in as normal.
* If it is given with a value (``invoke compile --log=foo.log``) then the value
  is stored normally.
* If the flag is given with no value (``invoke compile --log``), it is treated
  as if it were a ``bool`` and set to ``True``.

Resolving ambiguity
~~~~~~~~~~~~~~~~~~~

There are a number of situations where ambiguity could arise for a flag that
takes an optional value:

* When a task takes positional arguments and they haven't all been filled in by
  the time the parser arrives at the optional-value flag;
* When the token following one of these flags looks like it is itself a flag;
  or
* When that token has the same name as another task.

In most of these situations, Invoke's parser will `refuse the temptation to
guess
<http://zen-of-python.info/in-the-face-of-ambiguity-refuse-the-temptation-to-guess.html#12>`_
and raise an error.

However, in the case where the ambiguous token is flag-like, the current parse
context is checked to resolve the ambiguity:

- If the token is an otherwise legitimate argument, it is assumed that the user
  meant to give that argument immediately after the current one, and no
  optional value is set.

    - E.g. in ``invoke compile --log --verbose`` (assuming ``--verbose`` is
      another legit argument for ``compile``) the parser decides the user meant
      to give ``--log`` without a value, and followed it up with the
      ``--verbose`` flag.

- Otherwise, the token is interpreted literally and stored as the value for
  the current flag.

    - E.g. if ``--verbose`` is *not* a legitimate argument for ``compile``,
      then ``invoke compile --log --verbose`` causes the parser to assign
      ``"--verbose"`` as the value given to ``--log``. (This will probably
      cause other problems in our contrived use case, but it illustrates our
      point.)

.. _iterable-flag-values:

Iterable flag values
--------------------

A not-uncommon use case for CLI programs is the desire to build a list of
values for a given option, instead of a single value. While this *can* be done
via sub-string parsing -- e.g. having users invoke a command with ``--mylist
item1,item2,item3`` and splitting on the comma -- it's often preferable to
specify the option multiple times and store the values in a list (instead of
overwriting or erroring.)

In Invoke, this is enabled by hinting to the parser that one or more task
arguments are ``iterable`` in nature (similar to how one specifies ``optional``
or ``positional``)::

    @task(iterable=['my_list'])
    def mytask(c, my_list):
        print(my_list)

When not given at all, the default value for ``my_list`` will be an empty list;
otherwise, the result is a list, appending each value seen, in order, without
any other manipulation (so no deduplication, etc)::

    $ inv mytask
    []
    $ inv mytask --my-list foo
    ['foo']
    $ inv mytask --my-list foo --my-list bar
    ['foo', 'bar']
    $ inv mytask --my-list foo --my-list bar --my-list foo
    ['foo', 'bar', 'foo']

.. _incrementable-flag-values:

Incrementable flag values
-------------------------

This is arguably a sub-case of :ref:`iterable flag values
<iterable-flag-values>` (seen above) - it has the same core interface of "give
a CLI argument multiple times, and have that do something other than error or
overwrite a single value." However, 'incrementables' (as you may have guessed)
increment an integer instead of building a list of strings. This is commonly
found in verbosity flags and similar functionality.

An example of exactly that::

    @task(incrementable=['verbose'])
    def mytask(c, verbose=0):
        print(verbose)

And its use::

    $ inv mytask
    0
    $ inv mytask --verbose
    1
    $ inv mytask -v
    1
    $inv mytask -vvv
    3

Happily, because in Python ``0`` is 'falsey' and ``1`` (or any other number) is
'truthy', this functions a lot like a boolean flag as well, at least if one
defaults it to ``0``.

.. note::
    You may supply any integer default value for such arguments (it simply
    serves as the starting value), but take care that consumers of the argument
    are written understanding that it is always going to appear 'truthy' unless
    it's ``0``!

Dashes vs underscores in flag names
-----------------------------------

In Python, it's common to use ``underscored_names`` for keyword arguments,
e.g.::

    @task
    def mytask(c, my_option=False):
        pass

However, the typical convention for command-line flags is dashes, which aren't
valid in Python identifiers::

    $ inv mytask --my-option

Invoke works around this by automatically generating dashed versions of
underscored names, when it turns your task function signatures into
command-line parser flags.

Therefore, the two examples above actually work fine together -- ``my_option``
ends up mapping to ``--my-option``.

In addition, leading (``_myopt``) and trailing (``myopt_``) underscores are
ignored, since ``invoke ---myopt`` and ``invoke --myopt-`` don't make much
sense.

.. _boolean-flags:

Automatic Boolean inverse flags
-------------------------------

Boolean flags tend to work best when setting something that is normally
``False``, to ``True``::

    $ inv mytask --yes-please-do-x

However, in some cases, you want the opposite - a default of ``True``, which
can be easily disabled. For example, colored output::

    @task
    def run_tests(c, color=True):
        # ...

Here, what we really want on the command line is a ``--no-color`` flag that
sets ``color=False``. Invoke handles this for you: when setting up CLI flags,
booleans which default to ``True`` generate a ``--no-<name>`` flag instead.


.. _how-tasks-run:

How tasks run
=============

Base case
---------

In the simplest case, a task with no pre- or post-tasks runs one time.
Example::

    @task
    def hello(c):
        print("Hello, world!")

Execution::

    $ inv hello
    Hello, world!

.. _pre-post-tasks:

Pre- and post-tasks
-------------------

Tasks that should always have another task executed before or after them, may
use the ``@task`` deocator's ``pre`` and/or ``post`` kwargs, like so::

    @task
    def clean(c):
        print("Cleaning")

    @task
    def publish(c):
        print("Publishing")

    @task(pre=[clean], post=[publish])
    def build(c):
        print("Building")

Execution::

    $ inv build
    Cleaning
    Building
    Publishing

These keyword arguments always take iterables. As a convenience, pre-tasks (and
pre-tasks only) may be given as positional arguments, in a manner similar to
build systems like ``make``. E.g. we could present part of the above example
as::

    @task
    def clean(c):
        print("Cleaning")

    @task(clean)
    def build(c):
        print("Building")

As before, ``invoke build`` would cause ``clean`` to run, then ``build``.

Recursive/chained pre/post-tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-tasks of pre-tasks will also be invoked (as will post-tasks of pre-tasks,
pre-tasks of post-tasks, etc) in a depth-first manner, recursively. Here's a
more complex (if slightly contrived) tasks file::

    @task
    def clean_html(c):
        print("Cleaning HTML")

    @task
    def clean_tgz(c):
        print("Cleaning .tar.gz files")

    @task(clean_html, clean_tgz)
    def clean(c):
        print("Cleaned everything")

    @task
    def makedirs(c):
        print("Making directories")

    @task(clean, makedirs)
    def build(c):
        print("Building")

    @task(build)
    def deploy(c):
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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, pre- and post-tasks are executed with no arguments, even if the
task triggering their execution was given some. When this is not suitable, you
can wrap the task objects with `~.tasks.call` objects which allow you to
specify a call signature::

    @task
    def clean(c, which=None):
        which = which or 'pyc'
        print("Cleaning {}".format(which))

    @task(pre=[call(clean, which='all')]) # or call(clean, 'all')
    def build(c):
        print("Building")

Example output::

    $ inv build
    Cleaning all
    Building


.. _deduping:

Task deduplication
------------------

By default, any task that would run more than once during a session (due e.g.
to inclusion in pre/post tasks), will only be run once. Example task file::

    @task
    def clean(c):
        print("Cleaning")

    @task(clean)
    def build(c):
        print("Building")

    @task(build)
    def package(c):
        print("Packaging")

With deduplication turned off (see below), the above would execute ``clean`` ->
``build`` -> ``build`` again -> ``package``. With deduplication, the double
``build`` does not occur::

    $ inv build package
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
~~~~~~~~~~~~~~~~~~~~~~~

If you prefer your tasks to run every time no matter what, you can give the
``--no-dedupe`` core CLI option at runtime, or set the ``tasks.dedupe``
:doc:`config setting </concepts/configuration>` to ``False``. While it
doesn't make a ton of real-world sense, let's imagine we wanted to apply
``--no-dedupe`` to the above example; we'd see the following output::

    $ inv --no-dedupe build package
    Cleaning
    Building
    Building
    Packaging

The build step is now running twice.
