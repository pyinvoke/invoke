===============
Getting started
===============

This document presents a whirlwind tour of Invoke's feature set. Please see the
links throughout for detailed conceptual & API docs.

Defining and running task functions
===================================

The core use case for Invoke is setting up a collection of task functions and
executing them. This is pretty easy -- all you need is to make a file called
``tasks.py`` importing the `.task` decorator and decorating one or more
functions. Let's start making a Sphinx docs building task::

    from invoke import task

    @task
    def build():
        print("Building!")

You can then execute that new task by telling Invoke's command line runner,
``invoke``, that you want it to run::

    $ invoke build
    Building!

The function body can be any Python you want -- anything at all.

Parameterizing tasks
====================

Functions can have arguments, and thus so can tasks. By default, your task
functions' args/kwargs are mapped automatically to both long and short CLI
flags, as per :doc:`the CLI docs <concepts/cli/intro>`. For example, if we add
a ``clean`` argument and give it a boolean default, it will show up as a set of
toggle flags, ``--clean`` and ``-c``::

    @task
    def build(clean=False):
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
    def hi(name):
        print("Hi %s!" % name)

It can be invoked in the following ways, all resulting in "Hi Jeff!"::

    $ invoke hi Jeff
    $ invoke hi --name Jeff
    $ invoke hi --name=Jeff
    $ invoke hi -n Jeff
    $ invoke hi -nJeff

Again, more details on how all this works can be found in the :doc:`CLI
concepts <concepts/cli>`.

Listing tasks
=============

You'll sometimes want to see what tasks are available in a given
``tasks.py`` -- ``invoke`` can be told to list them instead of executing
something::

    $ invoke --list
    Available tasks:

        build

To see what else is available besides ``--list``, say ``invoke --help``.

Running shell commands
======================

Many use cases for Invoke involve running local shell commands, similar to
programs like Make or Rake. This is done via the `.run` function::

    from invoke import task, run

    @task
    def build():
        run("sphinx-build docs docs/_build")

You'll see the command's output in your terminal as it runs::

    $ invoke build
    Running Sphinx v1.1.3
    loading pickled environment... done
    ...
    build succeeded, 2 warnings.

`.run` returns a useful `.Result` object providing access to the captured
output, exit code, and so forth; it also allows you to activate a PTY, hide
output (so it is captured only), and more. See `its API docs <.run>` for
details.

Declaring pre-tasks
===================

Tasks may be configured in a number of ways via the `.task` decorator. One of
these is to select one or more other tasks you wish to always run prior to
execution of your task, indicated by name.

Let's expand our docs builder with a new cleanup task that runs before every
build (but which, of course, can still be executed on its own)::

    from invoke import task, run

    @task
    def clean():
        run("rm -rf docs/_build")

    @task('clean')
    def build():
        run("sphinx-build docs docs/_build")

Now when you ``invoke build``, it will automatically run ``clean`` first.

.. note::
    If you're not a fan of the implicit "positional arguments are pre-run task
    names" API, you can simply give the ``pre`` kwarg:
    ``@task(pre=['clean'])``.

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

Then we can use a new API member, the `.Collection` class, to bind this new
task and the ``docs`` module of tasks, into a single explicit namespace. This
typically occurs at the bottom of ``tasks.py`` once all the other objects have
been defined, like so::

    from invoke import Collection, task, run
    import docs

    @task
    def deploy():
        run("python setup.py sdist register upload")

    namespace = Collection(docs, deploy)

The result::

    $ invoke --list
    Available tasks:

        deploy
        docs.build
        docs.clean

For a more detailed breakdown of how namespacing works, please see :doc:`the
docs <concepts/namespaces>`.
