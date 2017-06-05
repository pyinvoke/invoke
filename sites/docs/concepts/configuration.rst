.. _configuration:

=============
Configuration
=============

Introduction
============

Invoke offers a fully fleshed out configuration mechanism allowing you to
configure both its core behavior (and that of your tasks) via a hierarchy of
configuration files, environment variables, :doc:`task namespaces
</concepts/namespaces>` and CLI flags.

The end result of configuration seeking, loading, parsing & merging, is a
`.Config` object, which behaves like a (nested) Python dictionary. Invoke
references this object when it runs (determining the default behavior of
methods like `.Context.run`) and exposes it to users' tasks as
`.Context.config` and as shorthand attribute access on the `.Context` itself.


.. _config-hierarchy:

The configuration hierarchy
===========================

In brief, the order in which configuration values override one another is as
follows:

#. **Internal default values** for behaviors which are controllable via
   configuration. See :ref:`default-values` for details.
#. **Collection-driven configurations** defined in tasks modules via
   `.Collection.configure`. (See :ref:`collection-configuration` below for
   details.)
   
     * Sub-collections' configurations get merged into the top level collection
       and the final result forms the basis of the overall configuration setup.
     * Since the root collection is loaded at runtime, configuration settings
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
#. **Command-line flags** for certain core settings, such as :option:`-e`.
#. **Modifications made by user code** at runtime.


.. _default-values:

Default configuration values
============================

Below is a list of all the configuration values and/or section Invoke itself
uses to control behaviors such as `.Context.run`'s ``echo`` and ``pty``
flags, task deduplication, and so forth.

.. note::
    The storage location for these values is inside the `.Config` class,
    specifically as the return value of `.Config.global_defaults`; see its API
    docs for more details.

For convenience, we refer to nested setting names with a dotted syntax, so e.g.
``foo.bar`` refers to what would be (in a Python config context) ``{'foo':
{'bar': <value here>}}``. Typically, these can be read or set on `.Config` and
`.Context` objects using attribute syntax, which looks nearly identical:
``ctx.foo.bar``.

* The ``tasks`` config tree holds settings relating to task execution.

  * ``tasks.dedupe`` controls :ref:`deduping` and defaults to ``True``. It can
    also be overridden at runtime via :option:`--no-dedupe`.

* The ``run`` tree controls the behavior of `.Runner.run`. Each member of this
  tree (such as ``run.echo`` or ``run.pty``) maps directly to a `.Runner.run`
  keyword argument of the same name; see that method's docstring for details on
  what these settings do & what their default values are.
* The ``runners`` tree controls _which_ runner classes map to which execution
  contexts; if you're using Invoke by itself, this will only tend to have a
  single member, ``runners.local``. Client libraries may extend it with
  additional key/value pairs, such as ``runners.remote``.
* The ``sudo`` tree controls the behavior of `.Context.sudo`:

    * ``sudo.password`` controls the autoresponse password submitted to sudo's
      password prompt. Default: ``None``.

      .. warning::
        While it's possible to store this setting, like any other, in
        :doc:`configuration files </concepts/configuration>` -- doing so is
        inherently insecure. We highly recommend filling this config value in
        at runtime from a secrets management system of some kind.

    * ``sudo.prompt`` holds the sudo password prompt text, which is both
      supplied to ``sudo -p``, and searched for when performing
      :doc:`auto-response </concepts/watchers>`. Default: ``[sudo] password:``.

* A top level config setting, ``debug``, controls whether debug-level output is
  logged; it defaults to ``False``.
  
  ``debug`` can be toggled via the :option:`-d` CLI flag, which enables
  debugging after CLI parsing runs. It can also be toggled via the
  ``INVOKE_DEBUG`` environment variable which - unlike regular env vars - is
  honored from the start of execution and is thus useful for troubleshooting
  parsing and/or config loading.


.. _config-files:

Configuration files
===================

Loading
-------

For each configuration file location mentioned in the previous section, we
search for files ending in ``.yaml``, ``.yml``, ``.json`` or ``.py`` (**in that
order!**), load the first one we find, and ignore any others that might exist.

For example, if Invoke is run on a system containing both ``/etc/invoke.yml``
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

For further details, see these languages' own documentation.


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
``foobar`` setting in a configuration file or in your task collections.

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
value of a given setting is used as a guide in casting the strings we get back
from the shell:

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
* Lists and tuples are currently unsupported and will raise an exception;

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
and refuse to guess; an error is raised instead, counseling users to modify
their configuration layout or avoid using env vars for the setting in question.


.. _collection-configuration:

`.Collection`-based configuration
=================================

`.Collection` objects may contain a config mapping, set via
`.Collection.configure`, and (as per :ref:`the hierarchy <config-hierarchy>`)
this typically forms the lowest level of configuration in the system.

When collections are :doc:`nested </concepts/namespaces>`, configuration is
merged 'downwards' by default: when conflicts arise, outer namespaces closer to
the root will win, versus inner ones closer to the task being invoked.

.. note::
    'Inner' tasks here are specifically those on the path from the root to the
    one housing the invoked task. 'Sibling' subcollections are ignored.

A quick example of what this means::

    from invoke import Collection, task

    # This task & collection could just as easily come from
    # another module somewhere.
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


Example of real-world config use
================================

The previous sections had small examples within them; this section provides a
more realistic-looking set of examples showing how the config system works.

Setup
-----

We'll start out with semi-realistic tasks that hardcode their values, and build
up to using the various configuration mechanisms. A small module for building
`Sphinx <http://sphinx-doc.org>`_ docs might begin like this::

    from invoke import task

    @task
    def clean(ctx):
        ctx.run("rm -rf docs/_build")

    @task
    def build(ctx):
        ctx.run("sphinx-build docs docs/_build")

Then maybe you refactor the build target::

    target = "docs/_build"

    @task
    def clean(ctx):
        ctx.run("rm -rf {0}".format(target))

    @task
    def build(ctx):
        ctx.run("sphinx-build docs {0}".format(target))

We can also allow runtime parameterization::

    default_target = "docs/_build"

    @task
    def clean(ctx, target=default_target):
        ctx.run("rm -rf {0}".format(target))

    @task
    def build(ctx, target=default_target):
        ctx.run("sphinx-build docs {0}".format(target))

This task module works for a single set of users, but what if we want to allow
reuse? Somebody may want to use this module with a different default target.
Using the configuration data (made available via the context arg) to configure
these settings is usually the better solution [1]_.

Configuring via task collection
-------------------------------

The configuration `setting <.Collection.configure>` and `getting
<.Context.config>` APIs make it easy to move otherwise 'hardcoded' default
values into a config structure which downstream users are free to redefine.
Let's apply this to our example. First we add an explicit namespace object::

    from invoke import Collection, task

    default_target = "docs/_build"

    @task
    def clean(ctx, target=default_target):
        ctx.run("rm -rf {0}".format(target))

    @task
    def build(ctx, target=default_target):
        ctx.run("sphinx-build docs {0}".format(target))

    ns = Collection(clean, build)

Then we can move the default build target value into the collection's default
configuration, and refer to it via the context. At this point we also change
our kwarg default value to be ``None`` so we can determine whether or not a
runtime value was given.  The result::

    @task
    def clean(ctx, target=None):
        if target is None:
            target = ctx.sphinx.target
        ctx.run("rm -rf {0}".format(target))

    @task
    def build(ctx, target=None):
        if target is None:
            target = ctx.sphinx.target
        ctx.run("sphinx-build docs {0}".format(target))

    ns = Collection(clean, build)
    ns.configure({'sphinx': {'target': "docs/_build"}})

The result isn't significantly more complex than what we began with, and as
we'll see next, it's now trivial for users to override your defaults in various
ways.

Configuration overriding
------------------------

The lowest-level override is, of course, just modifying the local `.Collection`
tree into which a distributed module has been imported. E.g. if the above
module is distributed as ``myproject.docs``, someone can define a ``tasks.py``
that does this::

    from invoke import Collection, task
    from myproject import docs

    @task
    def mylocaltask(ctx):
        # Some local stuff goes here
        pass

    # Add 'docs' to our local root namespace, plus our own task
    ns = Collection(mylocaltask, docs)

And then they can simply add this to the bottom::

    # Our docs live in 'built_docs', not 'docs/_build'
    ns.configure({'sphinx': {'target': "built_docs"}})

Now we have a ``docs`` sub-namespace whose build target defaults to
``built_docs`` instead of ``docs/_build``. Runtime users can still override
this via flags (e.g. ``inv docs.build --target='some/other/dir'``) just as
before.

If you prefer configuration files over in-Python tweaking of your namespace
tree, that works just as well; instead of adding the line above to the previous
snippet, instead drop this into a file next to ``tasks.py`` named
``invoke.yaml``::

    sphinx:
        target: built_docs

For this example, that sort of local-to-project conf file makes the most sense,
but don't forget that the :ref:`config hierarchy <config-hierarchy>` offers
additional configuration methods which may be suitable depending on your needs.


.. rubric:: Footnotes

.. [1]
    Copying and modifying the file breaks code reuse; overriding the
    module-level ``default_path`` variable won't play well with concurrency;
    wrapping the tasks with different default arguments works but is fragile
    and adds boilerplate.
