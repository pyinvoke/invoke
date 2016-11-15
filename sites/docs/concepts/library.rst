=========================
Using Invoke as a library
=========================

Invoke was designed for its constituent parts to be usable independently,
either out of the box or with a minimum of extra work by the maintainers. CLI
parsing, subprocess command execution, task organization, etc, are all written
as broadly separated concerns.

This document outlines use cases already known to work (because downstream
tools like `Fabric <http://fabfile.org>`_ are already utilizing them).


.. _reusing-as-a-binary:

Reusing Invoke as a distinct binary 
====================================

A major use case is distribution of your own program using Invoke under the
hood, bound to a different binary name, and usually setting a specific task
:doc:`namespace </concepts/namespaces>` as the default. In some cases,
removing, replacing and/or adding core CLI flags is also desired.

Getting set up
--------------

Say you want to distribute a test runner called ``tester`` offering two
subcommands, ``unit`` and ``integration``, such that users could ``pip install
tester`` and have access to commands like ``tester unit``, ``tester
integration``, or ``tester integration --fail-fast``.

First, as with any distinct Python package providing CLI
'binaries', you'd inform your ``setup.py`` of your entrypoint::

    setup(
        name='tester',
        version='0.1.0',
        packages=['tester'],
        install_requires=['invoke'],
        entry_points={
            'console_scripts': ['tester = tester.main:program.run']
        }
    )

.. note::
    This is not a fully valid ``setup.py``; if you don't know how Python
    packaging works, a good starting place is `the Python Packaging User's
    Guide <https://python-packaging-user-guide.readthedocs.io/en/latest/>`_.

Nothing here is specific to Invoke - it's a standard way of telling Python to
install a ``tester`` script that executes the ``run`` method of a ``program``
object defined inside the module ``tester.main``.

Creating a ``Program``
----------------------

In our ``tester/main.py``, we start out importing Invoke's public CLI
functionality::

    from invoke import Program

Then we define the ``program`` object we referenced in ``setup.py``, which is a
simple `.Program` to do the heavy lifting, giving it our version number for
starters::

    program = Program(version='0.1.0')

At this point, installing ``tester`` would give you the same functionality as
Invoke's :doc:`built-in CLI tool </cli>`, except named ``tester`` and exposing
its own version number::

    $ tester --version
    Tester 0.1.0
    $ tester --help
    Usage: tester [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

    Core options:
        ... core Invoke options here ... 

    $ tester --list
    Can't find any collection named 'tasks'!

This doesn't do us much good yet - there aren't any subcommands (and our users
don't care about arbitrary 'tasks', so Invoke's own default ``--help`` and
``--list`` output isn't a good fit).

Specifying subcommands
----------------------

For ``tester`` to expose ``unit`` and ``integration`` subcommands, we need to
define them, in a regular Invoke tasks module or :doc:`namespace
</concepts/namespaces>`. For our example, we'll just create ``tester/tasks.py``
(but as you'll see in a moment, this too is arbitrary and can be whatever you
like)::

    from invoke import task

    @task
    def unit(ctx):
        print("Running unit tests!")

    @task
    def integration(ctx):
        print("Running integration tests!")

As described in :doc:`/concepts/namespaces`, you can arrange this module
however you want - the above snippet uses an implicit namespace for brevity's
sake.

.. note::
    It's important to realize that there's nothing special about these
    "subcommands" - you could run them just as easily with vanilla Invoke,
    e.g. via ``invoke --collection=tester.tasks --list``.

Now the useful part: telling our custom `.Program` that this namespace of tasks
should be used as the subcommands for ``tester``, via the ``namespace`` kwarg::

    from invoke import Program, Collection
    from tester import tasks

    program = Program(namespace=Collection.from_module(tasks), version='0.1.0')

The result?

::

    $ tester --version
    Tester 0.1.0
    $ tester --help
    Usage: tester [--core-opts] <subcommand> [--subcommand-opts] ...

    Core options:
      ... core options here, minus task-related ones ...

    Subcommands:
      unit
      integration

    $ tester --list
    No idea what '--list' is!
    $ tester unit
    Running unit tests!

Notice how the 'usage' line changed (to specify 'subcommands' instead of
'tasks'); the list of specific subcommands is now printed as part of
``--help``; and ``--list`` has been removed from the options.

Modifying core parser arguments
-------------------------------

A common need for this use case is tweaking the core parser arguments.
`.Program` makes it easy: default core `Arguments <.Argument>` are returned by
`.Program.core_args`. Extend this method's return value with ``super`` and
you're done::

    # Presumably, this is your setup.py-designated CLI module...

    from invoke import Program, Argument

    class MyProgram(Program):
        def core_args(self):
            core_args = super(MyProgram, self).core_args()
            extra_args = [
                Argument(names=('foo', 'f'), help="Foo the bars"),
                # ...
            ]
            return core_args + extra_args

    program = MyProgram()

.. warning::
    We don't recommend *omitting* any of the existing core arguments; a lot of
    basic functionality relies on their existence, even when left to default
    values.

Wrap-up
-------

At this point you've got a nicely packaged program ready for distribution, with
no obvious hints that it's driven by Invoke. We've only shown a handful of the
options `.Program` provides - see its API docs for details on what else it can
do.
