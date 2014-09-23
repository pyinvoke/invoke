=============
Configuration
=============

Introduction
============

Invoke offers a fully fleshed out configuration mechanism (largely driven by a
vendored install of the etcaetera_ library) allowing you to configure both its
core behavior (and that of your tasks) via a hierarchy of configuration files,
environment variables, :doc:`task namespaces </concepts/namespaces>` and CLI
flags.

The end result of configuration seeking, loading, parsing & merging, is an
`etcaetera.Config
<http://etcaetera.readthedocs.org/en/latest/howto.html#config-object>`_ object,
which behaves like a (nested) Python dictionary. Invoke references this object
when it runs (determining the default behavior of methods like `~.Context.run`)
and exposes it to users' tasks as the `~.Context.config` attribute on
`.Context` objects.


The configuration hierarchy
===========================

In brief, the order in which configuration values are loaded (and overridden -
each new level overrides the one above it) is as follows:

#. **Collection-driven configurations** defined in tasks modules via
   `.Collection.configure`. (See :ref:`collection-configuration` below for
   details.)
   
     * Sub-collections' configurations get merged into the top level collection
       and the final result forms the basis of the overall configuration setup.
     * Since the root collection is loaded at runtime, configuration options
       modifying the load process itself obviously won't take effect if defined
       at this level.

#. **System-level configuration file** stored in ``/etc/``, such as
   ``/etc/invoke.yaml``. (See :ref:`config-files` for details on this and the
   other config-file entries.)
#. **User-level configuration file** found in the running user's home
   directory, e.g. ``~/.invoke.yaml``.
#. **Project-level configuration file** living next to your top level
   ``tasks.py``. For example, if your run of Invoke loads
   ``/home/user/myproject/tasks.py`` (see our docs on :doc:`the load process
   </concepts/loading>`), this might be ``/home/user/myproject/invoke.yaml``.
#. **Environment variables** found in the invoking shell environment.

    * These aren't as strongly hierarchical as the rest, nor is the shell
      environment namespace owned wholly by Invoke, so we must rely on slightly
      verbose prefixing instead - see :ref:`env-vars` for details.

#. **Runtime configuration file** whose path is given to :option:`-f`, e.g.
   ``inv -f /random/path/to/config_file.yaml``.
#. **Command-line flags** for certain core options, such as :option:`-e`.


.. _config-files:

Configuration files
===================

Loading
-------

For each configuration file location mentioned in the previous section, we
search for files ending in ``.yaml``, ``.json`` or ``.py`` (**in that
order!**), load the first one we find, and ignore any others that might exist.

For example, if Invoke is run on a system containing both ``/etc/invoke.yaml``
*and* ``/etc/invoke.json``, **only the YAML file will be loaded**. This helps
keep things simple, both conceptually and in the implementation.

Format
------

Invoke's configuration allows arbitrary nesting, and thus so do our config file
formats. All three of the below examples result in a configuration equivalent
to ``{'debug': True, 'run': {'echo': True}}``:

* **YAML**

  .. code-block:: yaml

      debug: true
      run:
          echo: true

* **JSON**

  .. code-block:: javascript

      {
          "debug": true,
          "run": {
              "echo": true
          }
      }

* **Python**::

    debug = True
    run = {
        "echo": True
    }

For further details, see these languages' own documentation, and/or the
documentation for etcaetera_ , whose drivers we use to load the files.

.. note::
    We make use of Etcaetera's ``lowercase`` adapter to ensure all config
    names/keys end up presented to Invoke and your tasks as all-lowercase.
    Values are untouched.


.. _env-vars:

Environment variables
=====================

Environment variables are a bit different from other configuration-setting
methods, since they don't provide a clean way to nest configuration keys, and
are also implicitly shared amongst the entire system's installed application
base.

In addition, due to implementation concerns, env vars must be pre-determined by
the levels below them in the config hierarchy (in other words - env vars may
only be used to override existing config values). If you need Invoke to
understand a ``FOOBAR`` environment variable, you must first declare a
``foobar`` config option in a configuration file or in your task collections.

Basic rules
-----------

To mitigate the shell namespace problem, we simply prefix all our env vars with
``INVOKE_``.

Nesting is performed via underscore separation, so a setting that looks like
e.g. ``{'run': {'echo': True}}`` at the Python level becomes
``INVOKE_RUN_ECHO=1`` in a typical shell. See :ref:`env-var-nesting` below for
more on this.

Type casting
------------

.. TODO: Dedupe this with the CLI type casting stuff once it is matured.

Since env vars can only be used to override existing settings, the previous
value of a given config option is used as a guide in casting the strings we get
back from the shell:

* If the current value is a string or Unicode object, it is replaced with the
  value from the environment, with no casting whatsoever;

    * Depending on interpreter and environment, this means that a setting
      defaulting to a non-Unicode string type (eg a ``str`` on Python 2) may
      end up replaced with a Unicode string, or vice versa. This is intentional
      as it prevents users from accidentally limiting themselves to non-Unicode
      strings.

* If the current value is ``None``, it too is replaced with the string from the
  environment;
* Booleans are set as follows: ``0`` and the empty value/string (e.g.
  ``SETTING=``, or ``unset SETTING``, or etc) evaluate to ``False``, and any
  other value evaluates to ``True``.
* Lists and dicts are currently unsupported and will raise an exception;

    * In the future we may implement convenience transformations, such as
      splitting on commas to form a list; however since users can always
      perform such operations themselves, it may not be a high priority.

* All other types - integers, longs, floats, etc - are simply used as
  constructors for the incoming value.

    * For example, a ``foobar`` setting whose default value is the integer
      ``1`` will run all env var inputs through `int`, and thus ``FOOBAR=5``
      will result in the Python value ``5``, not ``"5"``.

.. _env-var-nesting:

Nesting vs underscored names
----------------------------

.. TODO: normalize terminology - settings? options? other?

Since environment variable keys are single strings, we must use some form of
string parsing to allow access to nested configuration settings. As mentioned
above, in basic use cases this just means using an underscore character:
``{'run': {'echo': True}}`` becomes ``INVOKE_RUN_ECHO=1``.

However, ambiguity is introduced when the settings names themselves contain
underscores: is ``INVOKE_FOO_BAR=baz`` equivalent to ``{'foo': {'bar':
'baz'}}``, or to ``{'foo_bar': 'baz'}``? Thankfully, because env vars can only
be used to modify settings declared at the Python level or in config files, we
simply look at the current state of the config to determine the answer.

There is still a corner case where *both* possible interpretations exist as
valid config paths (e.g. ``{'foo': {'bar': 'default'}, 'foo_bar':
'otherdefault'}``). In this situation, we honor the `Zen of Python
<http://zen-of-python.info/in-the-face-of-ambiguity-refuse-the-temptation-to-guess.html#12>`_
and refuse to guess; an error is raised instead counseling users to modify
their configuration layout or avoid using env vars for the option in question.


.. _collection-configuration:

`.Collection`-based configuration
=================================

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
including ones set on the loaded `.Collection` objects. The
`.Collection.configure` method associates keys and values, which are then
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


.. _etcaetera: http://etcaetera.readthedocs.org/en/0.4.0

.. rubric:: Footnotes

.. [1]
    Copying and modifying the file breaks code reuse; overriding the
    module-level ``default_path`` variable won't play well with concurrency;
    wrapping the tasks with different default arguments works but is fragile
    and adds boilerplate.

