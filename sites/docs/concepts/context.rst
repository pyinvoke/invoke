.. _concepts-context:

=================================
Configuring behavior via contexts
=================================


A number of command-line flags and other configuration channels need to affect
global behavior: for example, controlling whether `~.runner.run` defaults to
echoing the commands it runs, or if nonzero return codes should abort
execution.

Some libraries implement this via global module state. That approach works in
the base case but makes testing difficult and error prone, limits concurrency,
and generally makes the software more complex to use and extend.

Invoke encapsulates core program state in a `~invoke.context.Context` object
which can be handed to individual tasks. It serves as a configuration vector
and implements state-aware methods mirroring the functional parts of the API.

Using contexts in your tasks
============================

To use Invoke's context-aware API, make the following changes to the task
definition style seen earlier:

* Tell `@task <.task>` that you want your task to be *contextualized* - given a
  `~invoke.context.Context` object - by saying ``contextualized=True``.

  .. note::
    See `Boilerplate reduction`_ below; this API is mostly for cleanness' sake.

* Define your task with an initial context argument; this argument is
  ignored during command-line parsing and is solely for context handling.

    * You can name it anything you want; Invoke uses it positionally, not via
      keyword. The convention used in the documentation is typically
      ``context`` or ``ctx``.

* Replace any mentions of `~.runner.run` with ``ctx.run`` (or whatever your
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

.. _configuration:

Using config values
===================

Using the context's ``run`` method to honor builtin options is only one use
case; your own code may want to store & retrieve configuration values as well.
This is especially useful in code you wish to distribute to others.

As an example, let's write a small module for building `Sphinx
<http://sphinx-doc.org>`_ docs. It might start out like this::

    from invoke import task, run

    @task
    def clean():
        run("rm -rf docs/_build")

    @task
    def build():
        run("sphinx-build docs docs/_build")

Then maybe you refactor the build target::

    target = "docs/_build"

    @task
    def clean():
        run("rm -rf {0}".format(target))

    @task
    def build():
        run("sphinx-build docs {0}".format(target))

We can also allow runtime parameterization::

    default_target = "docs/_build"

    @task
    def clean(target=default_target):
        run("rm -rf {0}".format(target))

    @task
    def build(target=default_target):
        run("sphinx-build docs {0}".format(target))

This task module works for a single set of users, but what if we want to allow
reuse? Somebody may want to use this module with a different default target.
You *can* kludge it using non-contextualized tasks, but using a context to
configure these options is usually the better solution [1]_.

From Collection to Context
--------------------------

The `~invoke.context.Context` objects offer access to various config options -
including ones set on the loaded `.Collection` objects.  `.Collections`'
`~.Collection.configure` method associates keys and values, which are then
available on the `~invoke.context.Context` via dict syntax.

This makes it easy to move otherwise 'hardcoded' default values into a config
structure which downstream users are free to redefine. Let's apply this to our
example. First we switch to using contextualized tasks and add an explicit
namespace object::

    from invoke import Collection, ctask as task

    default_target = "docs/_build"

    @task
    def clean(ctx, target=default_target):
        ctx.run("rm -rf {0}".format(target))

    @task
    def build(ctx, target=default_target):
        ctx.run("sphinx-build docs {0}".format(target))

    ns = Collection(clean, build)

Then we can move the default build target value into the collection, and refer
to it via the context. At this point we also change our kwarg default value to
be ``None`` so we can determine whether or not a runtime value was given.  The
result::

    @task
    def clean(ctx, target=None):
        ctx.run("rm -rf {0}".format(target or ctx['sphinx.target']))

    @task
    def build(ctx, target=None):
        ctx.run("sphinx-build docs {0}".format(target or ctx['sphinx.target']))

    ns = Collection(clean, build)
    ns.configure({'sphinx.target': "docs/_build"})

The result isn't significantly more complex than what we began with, and now
users can import your module and override your config defaults. E.g. if your
module is distributed as ``myproject.docs``, someone can define a ``tasks.py``
that does this::

    from invoke import Collection, ctask as task
    from myproject import docs

    @task
    def mylocaltask(ctx):
        # Some local stuff goes here
        pass

    # Add 'docs' to our local root namespace, plus our own task
    ns = Collection(mylocaltask, docs)
    # Override upstream configuration
    ns.configure({'sphinx.target': "built_docs"})

Now we have a ``docs`` sub-namespace whose build target defaults to
``built_docs`` instead of ``docs/_build``.

Nested namespace configuration merging
--------------------------------------

When :doc:`namespaces </concepts/namespaces>` are nested within one another,
configuration is merged 'downwards' by default: when conflicts arise, outer
namespaces win over inner ones (with 'inner' ones being specifically those on
the path from the root to the one housing the invoked task. 'Sibling'
subcollections are ignored.)

A quick example of what this means::

    from invoke import Collection, ctask as task

    # This task & collection could just as easily come from another module
    # somewhere.
    @task
    def mytask(ctx):
        print(ctx['conflicted'])
    inner = Collection('inner', mytask)
    inner.configure({'conflicted': 'default value'})

    # Our project's root namespace.
    ns = Collection(inner)
    ns.configure({'conflicted': 'override value'})

The result of calling ``inner.mytask``::

    $ inv inner.mytask
    override value



.. rubric:: Footnotes

.. [1]
    Copying and modifying the file breaks code reuse; overriding the
    module-level ``default_path`` variable won't play well with concurrency;
    wrapping the tasks with different default arguments works but is fragile
    and adds boilerplate.
