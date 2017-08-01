.. _task-execution:

==============
Task execution
==============

Invoke's task execution mechanisms provide a number of powerful features, while
attempting to ensure simple base cases aren't burdened with unnecessary
boilerplate. In this document we break down the concepts involved in executing
tasks, how tasks may relate to one another, and how to manage situations
arising from large task relationship graphs.


Basic concepts
==============

There are a handful of important terms here:

- **Tasks** are executable units of logic, i.e. instances of `Task`, which
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
- **Triggers**  (sometimes referred to as **post-tasks**) are roughly the
  inverse of dependencies - a task requesting that another task always be run
  sometime *after* it itself executes.

Now that we've framed the discussion, we can show you some concrete examples,
the features that enable them, and how those features interact with one
another.


One task
========

The simplest possible execution is simply to call a single task. Let's say we
have a ``build`` task might generate some output; we'll just print for now
instead, to make things easier to follow::

    from invoke import task

    @task
    def build(ctx):
        print("Building!")

Running it is trivial::

    $ inv build
    Building!


Multiple tasks
==============

Like ``make`` and (some) other task runners, you can call more than one task at
the same time. A classic example is to have a ``clean`` task that cleans up
previously generated output, which you'd call before the next ``build``::

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
=======================

Running multiple tasks at once is actually not the most common use case,
because anytime you have a common pattern it's good practice to make it happen
automatically. (Leaving the multiple-task use case for the uncommon situations
where you're mixing & matching tasks that are not usually run together.)

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
============

Another way to achieve the functionality shown in the previous section is to
leverage the concept of dependencies. This removes boilerplate from your task
bodies; and it lets you ensure that dependencies only run one time, even if
multiple tasks in a session would otherwise want to call them (covered in the
next section.)

Here's our nascent build task tree, using the ``dependencies`` kwarg to `@task
<.task>`::

    @task
    def clean(ctx):
        print("Cleaning!")

    @task(dependencies=[clean])
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

Of note, a convenient (and ``make``-esque) shortcut is to give ``dependencies``
as positional arguments to ``@task``; this is exactly the same as if one gave
an explicit iterable ``dependencies`` kwarg::

    @task(clean)
    def build(ctx):
        print("Building!")


Skipping execution via checks
=============================

To continue the "build" example (and to make it more concrete), let's say we
want to put some real behavior in place, and make some assertions about it.
Specifically:

- ``build`` is responsible for creating a file named ``output``
- ``build`` should not run if ``output`` already exists
  
  - Yes, this is a simplistic example!! If you're wondering about timestamps
  and hashes, this document isn't really for you; you may want to just skip
  over to the `checks module documentation <checks>`.)

- ``clean`` is responsible for removing ``output``
- ``clean`` should not run if ``output`` does not exist

.. note::
    We could phrase some of these constraints inside our tasks as well, but
    having the tests or predicates live outside task bodies lets us perform
    extra logic, as with dependencies. Which approach you use is up to you.

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

    import os
    from invoke import task

    @task(checks=[lambda: not os.path.exists('output')])
    def clean(ctx):
        print("Cleaning!")
        ctx.run("rm output")

    @task(dependencies=[clean], checks=[lambda: os.path.exists('output')])
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

Triggers
========

- single task w/ single trigger

    - note that unlike dependencies, triggered tasks are not cached per se, and
      are also pushed as late as possible (see below re: deduplication)

- commutative/recursive dependencies
- commutative/recursive triggers
- deduplication, i.e. task A depends on B, but explicit call is `inv B A` - is
  result `B B A` or just `B A`?

    - What about when A post-epends on B? `inv A B`, is that `A B B` or just `A
      B`?

    - What about real wacky shit like if A depends on B, but call is `inv A B`?
      is result `B A B` or just `B A` as in earlier example? (My gut says the
      former - as unlikely as this is, if A really needs B to run before it,
      then, that's what ya get!)

    - What about the #298 case of A post-ends on B, and C also post-ends on B?
      does `inv A C` become `A B C B`, or just `A C B`?

        - Go into the idea of loose vs tight binding (are there more official
          terms for this?) and note that if one wanted the former case, `A B C
          B` (or the dependency version, i.e. A and C depend on B, so would
          `inv A C` become `B A B C` or just `B A C`) one should phrase it
          within the body of `A` and `C`, because the dependency system is
          there to help you manage the deduplication - if you don't want
          deduplication then DON'T USE THE SYSTEM cuz it can't help you!
