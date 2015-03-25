.. _concepts-context:

===========================
State handling: the context
===========================

A common problem task runners face is transmission or storage of values which
are "global" for the current session - values loaded from :doc:`configuration
files <configuration>` (or :ref:`other configuration vectors
<collection-configuration>`), CLI flags, values set by 'setup' tasks, etc.

Some Python libraries (such as `Fabric <http://fabfile.org>`_ 1.x) implement
this via global module state. That approach works in the base case but makes
testing difficult and error prone, limits concurrency, and makes the software
more complex to use and extend.

Invoke encapsulates its state in an explicit `~.Context` object, handed to
tasks when they execute or instantiated and used by hand. The context is the
primary API endpoint, offering methods which honor the current state (such as
`.Context.run`) as well as access to that state itself.


Using contexts in your tasks
============================

To use Invoke's context-aware API, make the following changes to the task
definition style seen in the :doc:`tutorial </getting_started>`:

* Tell `@task <.task>` that you want your task to be *contextualized* - given a
  `.Context` object - by saying ``contextualized=True``.

  .. note::
    See `Boilerplate reduction`_ below; this API is mostly for cleanness' sake.

* Define your task with an initial context argument; this argument is
  ignored during command-line parsing and is solely for context handling.

    * You can name it anything you want; Invoke uses it positionally, not via
      keyword. The convention used in the documentation is typically
      ``context`` or ``ctx``.

* Replace any mentions of `~invoke.run` with ``ctx.run`` (or whatever your
  context argument's name was).

Here's a simple example::

    from invoke import task

    @task(contextualized=True)
    def restart(ctx):
        ctx.run("restart apache2")

We're using slightly more boilerplate than before (though see below), but your
``ctx.run`` calls will now honor command-line flags, config files and so forth.

Boilerplate reduction
---------------------

Specifying ``contextualized=True`` for every task in your collection would get
old fast. Invoke offers a convenience API call, `@ctask <.ctask>`, which is
effectively `@task <.task>` with ``contextualized`` set to ``True`` by default.

A common convention is to import it "as" ``task`` so things still look neat and
tidy::

    from invoke import ctask as task

    @task
    def restart(ctx):
        ctx.run("restart apache2")
