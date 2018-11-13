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

The previous sections outlined the syntax of describing which tasks you want to
run; however, the final sequence of what happens may differ from
that initial list, depending on your task definitions. Here's a quick list of
terms involved in how Invoke thinks about the work it's doing for you:

- **Tasks** are executable units of logic, i.e. instances of `.Task`, which
  typically wrap functions or other callables.
- Tasks may specify **checks** (typically functions) which allow skipping
  execution of a task if its desired result already seems to be complete (a
  file on disk exists, as with ``make``; a runtime configuration value has been
  set; etc).
- When called, tasks may be given **arguments**, same as any Python callable;
  these are typically seen as command-line flags when discussing the CLI.
- Tasks may be **parameterized** into multiple **calls**, e.g. invoking the
  same build procedure with different requested output formats, or executing a
  remote command on multiple target servers.
- **Dependencies** state that for a task to successfully execute, other tasks
  (sometimes referred to as **pre-tasks** or *prerequisites*) must be run
  sometime beforehand.
- **Followup tasks**  (sometimes referred to as **followups** or
  **post-tasks**) are roughly the inverse of dependencies - a task requesting
  that another task always be run sometime *after* it itself completes.

Now that we've framed the discussion, we can show you some concrete examples of
how these features behave and interact with one another.

One task
--------

The simplest possible execution is to call a single task. Let's say we have a
``build`` task which generates some output file; we'll just print for now
instead, to make things easier to follow::

    from invoke import task

    @task
    def build(c):
        print("Building!")

Running it does about as you'd expect::

    $ inv build
    Building!

Multiple tasks
--------------

Like ``make``, you can call more than one task at the same time. A classic
example is to have a ``clean`` task that cleans up previously generated output,
which you might call before a ``build`` to make sure previous build results
don't cause problems::

    @task
    def clean(c):
        print("Cleaning!")

    @task
    def build(c):
        print("Building!")

They run in the order requested::

    $ inv clean build
    Cleaning!
    Building!

Avoiding multiple tasks
-----------------------

Running the same set of tasks together on the CLI isn't actually done too often
-- users will quickly seek ways to avoid such frequent repetition, leaving the
multi-task use case to be useful in ad-hoc situations instead.

.. TODO: below may want to at least 'see also' link to any #170 solution

There are a few ways to avoid always calling ``inv clean build`` or similar;
the first requires no special features, instead leveraging the fact that Invoke
is straight-up Python: have ``build`` call ``clean`` directly, while preserving
``clean`` as a distinct task in case one ever needs to call it by hand::

    @task
    def clean(c):
        print("Cleaning!")

    @task
    def build(c):
        clean(c)
        print("Building!")

Executed::

    $ inv build
    Cleaning!
    Building!

Maybe you want to skip the ``clean`` step some of the time - it's easy enough
to add basic logic (note, we tweak the argument name to avoid overwriting which
object is bound to the local name ``clean``; trailing underscores are ignored
by the CLI parser, which makes this safe to do)::

    @task
    def clean(c):
        print("Cleaning!")

    @task
    def build(c, clean_=True):
        if clean_:
            clean(c)
        print("Building!")

The default behavior is the same as before, but now one can override the
auto-clean with ``--no-clean`` (using the parser's automatic ``--no-`` prefix
for Boolean arguments)::

    $ inv build
    Cleaning!
    Building!
    $ inv build --no-clean
    Building!

Dependencies
------------

Directly calling other tasks, as above, works fine initially but has a number
of minor-to-major disadvantages (especially as one leverages more of Invoke's
feature set). A more built-in way of describing these types of task
relationships is the concept of dependencies.

Declaring dependencies removes boilerplate from your task bodies and
signatures, and let you ensure dependencies only run once, even if multiple
tasks in a session would otherwise want to call them (an example of this is
covered in the next section.)

Here's our build task tree reimagined using dependencies, specifically the
``depends_on`` argument to `@task <.task>`::

    @task
    def clean(c):
        print("Cleaning!")

    @task(depends_on=clean)
    def build(c):
        print("Building!")

As with the inline call to ``clean()`` earlier, execution of ``build`` still
calls ``clean`` automatically by default; and you can use the core
``--no-dependencies`` flag to disable dependencies if necessary (replacing the
need for each task to set up its own variation on the earlier example's
``--no-clean``)::

    $ inv build
    Cleaning!
    Building!
    $ inv --no-dependencies build
    Building!

A convenient (and ``make``-esque) shortcut is to give dependencies as
positional arguments to ``@task``; this is exactly the same as if one gave an
explicit ``depends_on`` kwarg. For example, these two snippets are functionally
identical::

    @task(depends_on=clean)
    def build(c):
        pass

    @task(clean)
    def build(c):
        pass

as are these two (referencing another hypothetical ``check_config`` task, and
showing off how ``depends_on`` may take either a single callable or an iterable
of them)::

    @task(depends_on=[clean, check_config])
    def build(c):
        pass

    @task(clean, check_config)
    def build(c):
        pass

Skipping execution via checks
-----------------------------

To continue the "build" example (and make it more concrete), let's have it do
actual work, and make assertions about the results of that work. Specifically:

- ``build`` is responsible for creating a file named ``output``.
- ``build`` should not run if ``output`` already exists.
- ``clean`` is responsible for removing ``output``
- ``clean`` should not run if ``output`` does not exist

.. note::
    This is still a contrived example; we're purposely ignoring common tactics
    such as file modification timestamps, hashing, or commands like ``rm -f``.
    If you're already experienced with such things, consider heading straight
    to the `checks module documentation <invoke.checks>` instead.

To enable those behaviors, we add some `~Context.run` calls and use the
``check`` argument for `@task <.task>`, handing the latter a callable predicate
function. Checks may be arbitrary callables, which in Python usually means one
of the following:

- Inline ``lambda`` expressions, if one's expressions are trivial and need no
  reuse;
- Direct references to functions or instances of callable classes;
- Functions or instances returned *by* other functions (i.e. from *check
  factories*), which allow specifying behavior at interpretation time, while
  yielding something callable lazily at runtime.

.. TODO: is 'check factories' an actual thing we mention anywhere else?
.. TODO: or should we just make that a general reference to factories?

Our new, improved, slightly less trivial tasks file::

    from os.path import exists
    from invoke import task

    @task(check=lambda: not exists('output'))
    def clean(c):
        print("Cleaning!")
        c.run("rm output")

    @task(depends_on=clean, check=lambda: exists('output'))
    def build(c):
        print("Building!")
        c.run("touch output")

With these checks in place, we'd expect ``clean`` to only ever run if there is
something *to* clean, regardless of whether it's called explicitly or as a
dependency of ``build``. Sure enough, we don't see its ``print`` happen when
``output`` doesn't exist, in either case::

    $ ls
    tasks.py
    $ inv clean
    $ inv build
    Building!
    $ ls
    output  tasks.py

Now that our ``output`` file exists, ``clean`` will actually run the next time
we call it or ``build``::

    $ ls
    output  tasks.py
    $ inv build
    Cleaning!
    Building!

Finally, ``build`` would normally *always* run, because ``clean`` would always
clean up beforehand and cause ``build``'s check to trigger; but if we skip
dependencies, we'll find ``build`` short-circuits as expected if ``output`` is
already present::

    $ ls
    output  tasks.py
    $ inv --no-dependencies build
    $

.. TODO: add logging for this stuff and use that in these examples?
.. TODO: having explicit output would be nicer than 'did not print'

.. note::
    We could phrase some of these constraints as regular Python logic inside
    our tasks as well, but having the tests/predicates live outside tasks
    lets Invoke perform additional logic around them, similar to how
    dependencies work.

    Conversely, some situations that could be implemented via checks are made
    unnecessary by the existence of dependencies/followups, which use a graph
    mechanism to remove duplicate calls (see :ref:`recursive-dependencies`.)
    This means checks are mostly useful for allowing a task to run *zero*
    times, instead of *only once*.

    As always, we provide these tools but it's up to you to decide which of
    them apply best to your specific use case!

Followup tasks
--------------

Task dependencies are a common use case; less common is their inverse, calling
tasks automatically *after* an invoked task, instead of before. We refer to
these as "followup" tasks ("followups" in plural) and their `@task <.task>`
keyword is ``afterwards``.

For example, perhaps we want to invert the earlier example a bit, and build a
file purely for the purpose of uploading to a remote server. In such a
scenario, we may want to clean up at the end, lest we leave temporary files
lying around.

Here's a tasks file with tasks for building a tarball, uploading it to a
server, and cleaning up afterwards (note that we aren't using any checks in
this example, for simplicity)::

    @task
    def build(c):
        print("Building!")
        c.run("tar czf output.tgz source-directory")

    @task
    def clean(c):
        print("Cleaning!")
        c.run("rm output.tgz")

    @task(depends_on=build, afterwards=clean)
    def upload(c):
        print("Uploading!")
        c.run("scp output.tgz myserver:/var/www/")

Typically one would use these tasks like so::

    $ ls
    source-directory  tasks.py
    $ inv upload
    Building!
    Uploading!
    Cleaning!
    $ ls
    source-directory  tasks.py

Notice how the intermediate artifact, ``output.tgz``, isn't present after
execution, due to ``clean``.

Avoiding followups
------------------

As noted a few sections earlier, just because dependencies exist doesn't mean
they're the only appropriate solution for "call one thing before another."
Similarly, followups are useful, but they're best when you want some other task
to be called "eventually" (as opposed to "always right after"). They're also
not the best for situations where you want a followup to run *even if* the task
requesting them fails.

For example, say we want to ensure our build-and-upload task *never* leaves
files on disk. The previous snippet can't do this: if the network is down or
the user lacks the right key, an exception would be thrown, and Invoke would
never call ``clean``, leaving artifacts lying around.

In that case, you probably want to use generic Python ``try``/``finally``
statements::

    @task(depends_on=build)
    def upload(c):
        try:
            print("Uploading!")
            c.run("scp output.tgz myserver:/var/www/")
        finally:
            clean(c)

In this case, even if your ``scp`` were to fail, ``clean`` would still run.

.. _recursive-dependencies:

Recursive dependencies
----------------------

All of the above has focused on groups of tasks with simple, one-hop
relationships to each other. In the real world, things can be far messier. It's
quite possible to call one task, which depends on another, which depends on a
third, and so forth.

Multiple tasks in such a tree might share a dependency - and running it
multiple times in a session may be inefficient or even outright incorrect. Add
followup tasks to the mix and you've got quite a recipe for complexity.

Tools like Invoke tackle this by building a graph (technically, a *directed
acyclic graph* or *DAG*) of the requested tasks and their relationships, enabling
deduplication and determination of the correct execution order.

.. note::
    This deduplication does not require use of task checks (tasks are simply
    removed from the graph after they run), but the two features work well
    together nonetheless.

A quick example of what this looks like, with shared dependencies in a small
tree::

    @task
    def clean(c):
        print("Cleaning!")

    @task(clean)
    def build_one_thing(c):
        print("Building one thing!")

    @task(clean)
    def build_another_thing(c):
        print("Building another thing!!")

    @task(build_one_thing, build_another_thing)
    def build_all_the_things(c):
        print("BUILT ALL THE THINGS!!!")

And execution of the topmost task::

    $ inv build-all-the-things
    Cleaning!
    Building one thing!
    Building another thing!!
    BUILT ALL THE THINGS!!!

Note how ``clean`` only ran once, despite being a dependency of both
intermediate build steps (``build_one_thing`` and ``build_another_thing``). The
graph logic determined that running the four tasks in a specific order
satisfied all of the dependencies appropriately.

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
    def clean(c):
        print("Cleaning!")

    @task(clean)
    def build(c):
        print("Building!")

What should happen if one explicitly calls ``clean`` before ``build``, despite
it being implicitly depended upon? Should it run once, or twice?

This is sort of a trick question; from the perspective of a normal
(deduplicating) graph, we can't add the same item twice - it's effectively a
no-op. So ``clean`` will appear in the graph once, and only gets run once::

    $ inv clean build
    Cleaning!
    Building

Explicitly invoked followups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to previous, but with followups instead::

    @task
    def notify(c):
        print("Notifying!")

    @task(afterwards=notify)
    def test(c):
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

So we run ``inv build clean``...but should that second ``clean`` run, or not?

We've decided that in most cases, users will expect it *to* run the second
time, because they explicitly stated they wanted to "``build``, then
``clean``". The fact that building also implicitly includes a clean beforehand
shouldn't impact that. Thus, the result is::

    $ inv build clean
    Cleaning!
    Building!
    Cleaning!

.. note::
    On a technical level, this works with a DAG and doesn't create a cycle, for
    two reasons:

    - First, the "top level" explicitly-requested tasks are all added to the
      DAG by having later ones depend on earlier ones; so in this case,
      the explicitly requested ``clean`` temporarily depends on ``build``
      because it comes afterwards in the series.
    - However, these implicit dependencies *do not* mutate the original task:
      the nodes in the DAG which map to the tasks given on the CLI are actually
      'call' objects that lightly wrap the real tasks. You can think of them as
      clones or copies, from the graph's perspective.

    Thus, the main ``clean`` task is not modified to have a dependency on
    ``build``, and no cycle is created.

Multiple explicitly invoked tasks with the same followup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Say we've got two tasks which both want to be followed by the same, third
task::

    @task
    def notify(c):
        print("Notifying!")

    @task(afterwards=notify)
    def build(c):
        print("Building!")

    @task(afterwards=notify)
    def test(c):
        print("Testing!")

What happens if we run ``inv test build``? One could imagine a handful of
possible "expansions":

#. Both followups get triggered: ``test``, ``notify``, ``build``, and another ``notify``
#. Only one gets triggered, as early as possible: ``test``, ``notify``,
   ``build``. (Earlier versions of Invoke that didn't use a DAG ended up
   unintentionally selecting this option!)
#. Only one gets triggered, as late as possible: ``test``, ``build``,
   ``notify``.

If you guessed option 3, you're right - due to how we build the DAG, we
rephrase everything (including followups) as temporary dependencies, and end up
adding a reference to ``notify`` which has ``test`` and ``build`` as
dependencies. Therefore, it runs once, and only after those two tasks have
executed. Happily, this is typically what's desired.

.. note::
    Option 1, "I really wanted ``notify`` to run after *both* tasks!", is
    another example of when *not* to use the dependency tree. That case is a
    job for explicit invocation of ``notify`` at the end of one's task bodies.
