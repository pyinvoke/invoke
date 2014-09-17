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
which behaves like a set of nested dictionaries. Invoke then references this
object when it runs (determining the default behavior of functions like
`~.runner.run`) and exposes it to users' tasks as an attribute on
:doc:`contexts </concepts/context>`.


The configuration hierarchy
===========================

In brief, the order in which configuration values are loaded (and overridden -
each new level overrides the one above it) is as follows:

#. **Collection-driven configurations** defined in tasks modules via
   `.Collection.configure`.
   
     * Sub-collections' configurations get merged into the top level
       collection, as described in :doc:`the contexts documentation
       </concepts/context>`, and the final result forms the basis of the
       overall configuration setup.
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
   ``/home/user/myproject/tasks.py`` (see :doc:`our docs on the load process
   </concepts/loading>`), this might be ``/home/user/myproject/invoke.yaml``.
#. **Environment variables** found in the invoking shell environment.

    * These aren't as strongly hierarchical as the rest, nor is the shell
      environment namespace owned wholly by Invoke, so we must rely on slightly
      verbose prefixing instead - see :ref:`env-vars` for details.

#. **Runtime configuration file** whose path is given to :option:`-f`, e.g.
   ``inv -f /random/path/to/config_file.yaml``.
#. **Command-line flags**, either dedicated ones for core options (like
   :option:`-e`) or use of :option:`--set` which allows runtime overriding of
   arbitrary configuration paths.


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

* Env vars all prefixed with ``INVOKE_`` because we don't own the entire shell
  namespace and also don't want to manually declare everything (the other
  method of ensuring no conflicts).
* ``run.echo`` in collection configs == ``run: echo:`` in conf files ==
  ``INVOKE_RUN_ECHO``.
* Ambiguity between "underscore as level separator" and "underscore as part of
  level or variable name" is solved by a smart parser that knows what's
  available and can thus tell what a given underscore "is" (part of a valid
  name at that level, or not).

    * Because of this, env vars cannot be the original source of a variable -
      they must be modifying something defined in one of the other levels such
      as in-Python or config file.


.. _etcaetera: http://etcaetera.readthedocs.org/en/0.4.0
