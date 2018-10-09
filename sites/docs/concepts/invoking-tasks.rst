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

Basic concepts / terminology
----------------------------

.. TODO: flesh this out more with some sort of short intro?
.. TODO: seems like targets-vs-tasks was left unfinished, figure that out.

- **Tasks** are executable units of logic, i.e. instances of `.Task`, which
  typically wrap functions or other callables.
- Tasks may declare that their purpose is to produce some state (a file
  on-disk, as with ``make``; runtime configuration data; a database value; etc)
  and that they can be safely skipped if the configured **checks** pass.
- When called, targets may be given **arguments**, same as any Python callable;
  these are typically seen as command-line flags when discussing the CLI.
- Targets may be **parameterized** into multiple **calls**, e.g. invoking the
  same build procedure against multiple different file paths, or executing a
  remote command on multiple target servers.
- **Dependencies** state that for a task to successfully execute, other tasks
  (sometimes referred to as **pre-tasks** or, in ``make``, *prerequisites*)
  must be run sometime beforehand.
- **Followup tasks**  (sometimes referred to as **post-tasks**) are roughly the
  inverse of dependencies - a task requesting that another task always be run
  sometime *after* it itself executes.

Now that we've framed the discussion, we can show you some concrete examples,
the features that enable them, and how those features interact with one
another.

One task
--------

The simplest possible execution is to call a single task. Let's say we have a
``build`` task which generates some output file; we'll just print for now
instead, to make things easier to follow::

    from invoke import task

    @task
    def build(ctx):
        print("Building!")

Running it is trivial::

    $ inv build
    Building!


Multiple tasks
--------------

Like ``make`` and (some) other task runners, you can call more than one task at
the same time. A classic example is to have a ``clean`` task that cleans up
previously generated output, which you might call before a new ``build`` to
make sure previous build results don't cause problems::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task
    def build(ctx):
        print("Building!")

As you'd expect, they run in the order requested::

    $ inv clean build
    Cleaning!
    Building!


Avoiding multiple tasks
-----------------------

Running multiple tasks at once isn't actually a frequent practice -- because
anytime you have a common pattern, automating it is a smart move. (This leaves
the multiple-task use case for uncommon situations where you're mixing &
matching tasks that are not always run together.)

One way to do this requires no special help from Invoke, but simply leverages
typical Python logic: have ``build`` call ``clean`` automatically (while
preserving ``clean`` as a distinct task in case one ever needs to call it by
hand)::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task
    def build(ctx):
        clean(ctx)
        print("Building!")

Executed::

    $ inv build
    Cleaning!
    Building!

Maybe you don't want to clean some of the time - easy enough to add basic logic
(relying on mild name obfuscation to avoid name collisions - Invoke
automatically strips leading/trailing underscores when turning args into CLI
flags; and it creates ``--no-`` versions of default-true Boolean args as
well)::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task
    def build(ctx, clean_=True):
        if clean_:
            clean(ctx)
        print("Building!")

Default behavior is the same as before, but you can now override the auto-clean
with ``--no-clean``::

    $ inv build
    Cleaning!
    Building!
    $ inv build --no-clean
    Building!


Dependencies
------------

Another way to achieve the functionality shown in the previous section is to
leverage the concept of dependencies. This removes boilerplate from your task
bodies; and it lets you ensure that dependencies only run one time, even if
multiple tasks in a session would otherwise want to call them (covered in the
next section.)

Here's our nascent build task tree, using the ``depends_on`` kwarg to `@task
<.task>`::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task(depends_on=[clean])
    def build(ctx):
        print("Building!")

As with the inline call to ``clean()`` earlier, execution of ``build`` still
calls ``clean`` automatically by default; and you can use the core
``--no-dependencies`` flag to disable dependencies if necessary::

    $ inv build
    Cleaning!
    Building!
    $ inv --no-dependencies build
    Building!

.. note::
    A convenient (and ``make``-esque) shortcut is to give dependencies as
    positional arguments to ``@task``; this is exactly the same as if one gave
    an explicit, iterable ``depends_on`` kwarg. In other words, ``@task(clean)``
    is a shorter way of saying ``@task(depends_on=[clean])``; ``@task(clean,
    check_config)`` is equivalent to ``@task(depends_on=[clean,
    check_config])``; etc.


Skipping execution via checks
-----------------------------

To continue the "build" example (and make it more concrete), let's say we want
to put some real behavior in place, and make some assertions about it.
Specifically:

- ``build`` is responsible for creating a file named ``output``
- ``build`` should not run if ``output`` already exists

  - Yes, this is a simplistic example!! If you're wondering about timestamps
    and hashes, this document isn't really for you; you may want to just skip
    over to the `checks module documentation <invoke.checks>`.)

- ``clean`` is responsible for removing ``output``
- ``clean`` should not run if ``output`` does not exist

.. note::
    We could phrase some of these constraints inside our tasks as well, but
    having the tests or predicates live outside task bodies lets us perform
    extra logic, as with dependencies.

    Conversely, some situations that would make sense for checks are made
    unnecessary by the dependency/followup system, which uses a graph mechanism
    to remove duplicate calls (see :ref:`recursive-dependencies`.) This leaves
    checks primarily useful for causing a task to run *zero* times, instead of
    *only once*.

    As always, we provide these various tools, but it's up to you to decide
    which of them apply best to your specific use case.

To enable these behaviors, we update the task bodies to do real work; and we
use the ``check`` and/or ``checks`` kwargs to `@task <.task>`, handing them
callable predicate functions (or iterables of same.)

Checks may be arbitrary callables, typically taking a few forms:

- Inline lambdas, if one's expressions are trivial and need no reuse;
- Functions or other callables;
- Functions returned by other functions (i.e. from *check factories*), which
  allow specifying behavior at interpretation time, while yielding something
  callable lazily at runtime.

Our new, improved, slightly less trivial tasks file::

    from os.path import exists
    from invoke import task

    @task(check=lambda: not exists('output'))
    def clean(ctx):
        print("Cleaning!")
        ctx.run("rm output")

    @task(depends_on=[clean], check=lambda: exists('output'))
    def build(ctx):
        print("Building!")
        ctx.run("touch output")

With the checks in place, a session when ``output`` doesn't exist yet should
skip ``clean`` but run ``build``, and sure enough::

    $ ls
    tasks.py
    $ inv build
    Building!
    $ ls
    output  tasks.py

Conversely, now that ``output`` exists, ``clean`` will run - but only once::

    $ inv clean
    Cleaning!
    $ ls
    tasks.py
    $ inv clean
    $

Putting ``output`` back in place, we can see that ``clean`` still runs as a
dependency when it has a job to do, and only afterwards is ``build``'s check
consulted (and since things were cleaned, it gives the affirmative)::

    $ ls
    output  tasks.py
    $ inv build
    Cleaning!
    Building!

Finally, ``build`` would typically always run, because ``clean`` will always
clean up before it; but if we skip dependencies, we'll find ``build`` also
short-circuits when it has no work to do::

    $ ls
    output  tasks.py
    $ inv --no-dependencies build
    $ 

This is a highly contrived example, but hopefully illustrative.


Followup tasks
--------------

Task dependencies are a common use case; less common is their effective
inverse, calling tasks *after* the invoked task, instead of before. We refer to
these as "followup" tasks ("followups" in plural) and their `@task <.task>`
keyword is ``afterwards``.

For example, perhaps we want to invert the earlier example a bit, and build a
file purely for the purpose of uploading to a remote server. In such a
scenario, we may want to clean up at the end, lest we leave temporary files
lying around on disk.

Here's a tasks file with tasks for building a tarball, uploading it to a
server, and cleaning up afterwards::

    @task
    def build(ctx):
        print("Building!")
        ctx.run("tar czf output.tgz source-directory")

    @task
    def clean(ctx):
        print("Cleaning!")
        ctx.run("rm output.tgz")

    @task(depends_on=[build], afterwards=[clean])
    def upload(ctx):
        print("Uploading!")
        ctx.run("scp output.tgz myserver:/var/www/")

Typically one would use the tasks file like so::

    $ ls
    source-directory  tasks.py
    $ inv upload
    Building!
    Uploading!
    Cleaning!
    $ ls
    source-directory  tasks.py

Notice how the intermediate artifact, ``output.tgz``, isn't present after
things are all done, due to ``clean``.


Avoiding followups
------------------

As noted a few sections earlier, just because dependencies exist doesn't mean
they're the only appropriate solution for "call one thing before another."
Similarly, followups are useful, but they're best when you want some other task
to be called "eventually" (as opposed to "always right after".) They're also
not the best for situations where you want a followup to run *even if* the task
requesting them fails.

For example, say we want to ensure our build-and-upload task *never* leaves
files on disk. The previous snippet can't do this: if the network is down or
the user lacks the right key, an exception would be thrown, and Invoke would
never call ``clean``, leaving artifacts lying around.

In that case, you really just want to use ``try``/``finally``::

    @task(depends_on=[build])
    def upload(ctx):
        try:
            print("Uploading!")
            ctx.run("scp output.tgz myserver:/var/www/")
        finally:
            clean(ctx)

In this case, even if your ``scp`` were to fail, ``clean`` would still get a
shot at running.


.. _recursive-dependencies:

Recursive dependencies
----------------------

All of the above has focused on groups of tasks with simple, one-hop
relationships to each other. In the real world, things can be far messier. It's
quite possible to end up calling one task, which depends on another, which
depends on a third, which...you get the idea. Multiple tasks might share the
same dependency - running that dependency multiple times in a session is at
best inefficient and at worst incorrect. And once we add followups to the mix,
the complexity increases further.

Tools like Invoke tackle this by building a graph (technically, a *directed
acyclic graph* or *DAG*) of the tasks and their relationships, enabling
deduplication and determination of the best execution order.

.. note::
    This deduplication does not require use of task checks (tasks are simply
    removed from the graph after they run), but the two features work well
    together nonetheless.

A quick example of what this looks like: some shared dependencies in a small
tree::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task(clean)
    def build_one_thing(ctx):
        print("Building one thing!")

    @task(clean)
    def build_another_thing(ctx):
        print("Building another thing!!")

    @task(build_one_thing, build_another_thing)
    def build_all_the_things(ctx):
        print("BUILT ALL THE THINGS!!!")

And execution of the topmost task::

    $ inv build-all-the-things
    Cleaning!
    Building one thing!
    Building another thing!!
    BUILT ALL THE THINGS!!!

Note how ``clean`` only ran once, despite being a dependency of both of the
intermediate build steps.


Call graph edge cases
---------------------

Many edge cases can pop up when one starts combining dependencies, followups
and calling multiple tasks in the same CLI session; we enumerate most of these
below and note how the system is expected to behave when it encounters them.
Divergence from this behavior should be reported as a bug.

Explicitly invoked dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Given a ``build`` that depends on ``clean``::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task(clean)
    def build(ctx):
        print("Building!")

What should happen if one explicitly calls ``clean`` before ``build``, despite
it being implicitly depended upon? Should it run once, or twice?

This is actually sort of a trick question; from the perspective of a call
graph, we can't add the same task twice as a dependency of another - it's
effectively a no-op. So ``clean`` will end up only appearing in the graph once,
and only gets run once::

    $ inv clean build
    Cleaning!
    Building

Explicitly invoked followups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to previous, but with followups instead::

    @task
    def notify(ctx):
        print("Notifying!")

    @task(afterwards=[notify])
    def test(ctx):
        print("Testing!")

If one calls ``inv test notify``, should ``notify`` run once or twice? As
before, the graph says only once::

    $ inv test notify
    Testing!
    Notifying!

Explicity invoked dependencies given afterwards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What if a dependency is explicitly requested to run *after* a task that depends
on it? Referencing the ``clean``/``build`` example from before, where ``build``
depends on ``clean``, what if we wanted to test our build task and then clean
up afterwards (i.e. we're testing the act of building and don't truly care
about keeping the result, for now.)

So we run ``inv build clean``...but does that second ``clean`` actually run, or
not?

We've decided that in most cases, users will expect it *to* run the second
time, because they explicitly stated they wanted to "``build``, then
``clean``". The fact that building also implicitly includes a clean shouldn't
impact that. Thus, the result is::

    $ inv build clean
    Cleaning!
    Building!
    Cleaning!

.. note::
    On a technical level, this works with a DAG and doesn't create a cycle, for
    two reasons:

    - First, multiple explicitly requested tasks are added to the DAG by having
      later ones depend on earlier ones; so in this case, ``clean`` implicitly
      depends on ``build`` because it comes afterwards in the series.
    - However, these implicit dependencies *do not* mutate the original task:
      the nodes in the DAG which map to the tasks given on the CLI are actually
      'call' objects that lightly wrap the real tasks.
      
    Thus, the real ``clean`` task is not modified to have a dependency on
    ``build``, and no cycle is created.

Multiple explicitly invoked tasks with the same followup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Say we've got two tasks which both follow up with the same, third task::

    @task
    def notify(ctx):
        print("Notifying!")

    @task(afterwards=[notify])
    def build(ctx):
        print("Building!")

    @task(afterwards=[notify])
    def test(ctx):
        print("Testing!")

What happens if we run ``inv test build``? One could imagine a handful of
possible "expansions":

#. Both followups get triggered: ``test``, ``notify``, ``build``, and another ``notify``
#. Only one gets triggered, as early as possible: ``test``, ``notify``,
   ``build``. (Earlier versions of Invoke that didn't use a DAG ended up
   accidentally selecting this option!)
#. Only one gets triggered, as late as possible: ``test``, ``build``,
   ``notify``.

If you guessed option 3, you're right - due to how we build the DAG ("A follows
up with B" tends to get turned around into "B depends on A"), ``notify`` ends
up not being able to run until both ``build`` and ``test`` have executed.
Happily, this is typically what's desired.

.. note::
    Option 1, "I really wanted ``notify`` to run after *both* tasks!", is
    another example of when *not* to use the dependency tree. That case is a
    job for simple, explicit invocation of ``notify`` at the end of one's task
    bodies.
