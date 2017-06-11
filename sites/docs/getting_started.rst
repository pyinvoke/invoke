===============
Getting started
===============

This document presents a whirlwind tour of Invoke's feature set. Please see the
links throughout for detailed conceptual & API docs. For installation help, see
the project's `installation page <http://www.pyinvoke.org/installing.html>`_.

.. _defining-and-running-task-functions:

Defining and running task functions
===================================

The core use case for Invoke is setting up a collection of task functions and
executing them. This is pretty easy -- all you need is to make a file called
``tasks.py`` importing the `.task` decorator and decorating one or more
functions. You will also need to add an arbitrarily-named context argument
(convention is to use ``c``, ``ctx`` or ``context``) as the first positional
arg. Don't worry about using this context parameter yet.

Let's start with a dummy Sphinx docs building task::

    from invoke import task

    @task
    def build(ctx):
        print("Building!")

You can then execute that new task by telling Invoke's command line runner,
``invoke``, that you want it to run::

    $ invoke build
    Building!

The function body can be any Python you want -- anything at all.


Task parameters
===============

Functions can have arguments, and thus so can tasks. By default, your task
functions' args/kwargs are mapped automatically to both long and short CLI
flags, as per :doc:`the CLI docs <concepts/cli/intro>`. For example, if we add
a ``clean`` argument and give it a boolean default, it will show up as a set of
toggle flags, ``--clean`` and ``-c``::

    @task
    def build(ctx, clean=False):
        if clean:
            print("Cleaning!")
        print("Building!")

Invocations::

    $ invoke build -c
    $ invoke build --clean

Naturally, other default argument values will allow giving string or integer
values. Arguments with no default values are assumed to take strings, and can
also be given as positional arguments. Take this incredibly contrived snippet
for example::

    @task
    def hi(ctx, name):
        print("Hi {0}!".format(name))

It can be invoked in the following ways, all resulting in "Hi Jeff!"::

    $ invoke hi Jeff
    $ invoke hi --name Jeff
    $ invoke hi --name=Jeff
    $ invoke hi -n Jeff
    $ invoke hi -nJeff

Adding metadata via `@task <.task>`
-----------------------------------

`@task <.task>` can be used without any arguments, as above, but it's also a
convenient vector for additional metadata about the task function it decorates.
One common example is describing the task's arguments, via the ``help``
parameter (in addition to optionally giving task-level help via the
docstring)::

    @task(help={'name': "Name of the person to say hi to."})
    def hi(ctx, name):
        """
        Say hi to someone.
        """
        print("Hi {0}!".format(name))

This description will show up when invoking ``--help``::

    $ invoke --help hi
    Usage: inv[oke] [--core-opts] hi [--options] [other tasks here ...]

    Docstring:
      Say hi to someone.

    Options:
      -n STRING, --name=STRING   Name of the person to say hi to.

More details on task parameterization and metadata can be found in the
:doc:`CLI concepts <concepts/cli>` (for the command-line & parsing side of
things) and the `.task` API documentation (for the declaration side).


Listing tasks
=============

You'll sometimes want to see what tasks are available in a given
``tasks.py`` -- ``invoke`` can be told to list them instead of executing
something::

    $ invoke --list
    Available tasks:

        build

This will also print the first line of each task’s docstring, if it has one. To
see what else is available besides ``--list``, say ``invoke --help``.


Running shell commands
======================

Many use cases for Invoke involve running local shell commands, similar to
programs like Make or Rake. This is done via the `~.Context.run` function::

    from invoke import task, run

    @task
    def build(ctx):
        ctx.run("sphinx-build docs docs/_build")

You'll see the command's output in your terminal as it runs::

    $ invoke build
    Running Sphinx v1.1.3
    loading pickled environment... done
    ...
    build succeeded, 2 warnings.

`~.Context.run` returns a useful `.Result` object providing access to the
captured output, exit code, and so forth; it also allows you to activate a PTY,
hide output (so it is captured only), and more. See `its API docs
<.Context.run>` for details.

.. _why-context:

Aside: what exactly is this 'context' anyway?
---------------------------------------------

A common problem task runners face is transmission of "global" data - values
loaded from :doc:`configuration files </concepts/configuration>` or :ref:`other
configuration vectors <collection-configuration>`, given via CLI flags,
generated in 'setup' tasks, etc.

Some libraries (such as `Fabric <http://fabfile.org>`_ 1.x) implement this via
module-level attributes, which makes testing difficult and error prone, limits
concurrency, and increases implementation complexity.

Invoke encapsulates state in explicit `~.Context` objects, handed to tasks when
they execute . The context is the primary API endpoint, offering methods which
honor the current state (such as `.Context.run`) as well as access to that
state itself.


Declaring pre-tasks
===================

Tasks may be configured in a number of ways via the `.task` decorator. One of
these is to select one or more other tasks you wish to always run prior to
execution of your task, indicated by name.

Let's expand our docs builder with a new cleanup task that runs before every
build (but which, of course, can still be executed on its own)::

    from invoke import task

    @task
    def clean(ctx):
        ctx.run("rm -rf docs/_build")

    @task(clean)
    def build(ctx):
        ctx.run("sphinx-build docs docs/_build")

Now when you ``invoke build``, it will automatically run ``clean`` first.

.. note::
    If you're not a fan of the implicit "positional arguments are pre-run task
    names" API, you can simply give the ``pre`` kwarg:
    ``@task(pre=[clean])``.

Details can be found in the :doc:`execution conceptual docs
<concepts/execution>`.


Creating namespaces
===================

Right now, our ``tasks.py`` is implicitly for documentation only, but maybe our
project needs other non-doc things, like packaging/deploying, testing, etc. At
that point, a single flat namespace isn't enough, so Invoke lets you easily
build a :doc:`nested namespace <concepts/namespaces>`. Here's a quick example.

Let's first rename our ``tasks.py`` to be ``docs.py``; no other changes are
needed there. Then we create a new ``tasks.py``, and for the sake of brevity
populate it with a new, truly top level task called ``deploy``.

Finally, we can use a new API member, the `.Collection` class, to bind this new
task and the ``docs`` module into a single explicit namespace.  When Invoke
loads your task module, if a `.Collection` object bound as ``ns`` or
``namespace`` exists it will get used for the root namespace::

    from invoke import Collection, task
    import docs

    @task
    def deploy(ctx):
        ctx.run("python setup.py sdist register upload")

    namespace = Collection(docs, deploy)

The result::

    $ invoke --list
    Available tasks:

        deploy
        docs.build
        docs.clean

For a more detailed breakdown of how namespacing works, please see :doc:`the
docs <concepts/namespaces>`.
