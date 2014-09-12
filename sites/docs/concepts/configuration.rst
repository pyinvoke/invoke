=============
Configuration
=============

Introduction
============

Invoke offers a fully fleshed out configuration mechanism (largely driven by a
vendored install of the `etcaetera <http://etcaetera.readthedocs.org>`_
library) allowing you to configure both its core behavior (and that of your
tasks) via a hierarchy of configuration files, environment variables,
:doc:`task namespaces </concepts/namespaces>` and CLI flags.

The end result of configuration seeking, loading, parsing & merging, is an
`etcaetera.Config
<http://etcaetera.readthedocs.org/en/latest/howto.html#config-object>`_ object,
which behaves like a set of nested dictionaries. Invoke then references this
object when it runs (determining the default behavior of functions like `.run`)
and exposes it to users' tasks as an attribute on :doc:`contexts
</concepts/contexts>`.


The configuration hierarchy
===========================

In brief, the order in which configuration values are loaded (and overridden -
each new level overrides the one above it) is as follows:

* **Collection-driven configurations** defined in tasks modules via
  `.Collection.configure`.
  
    * Sub-collections' configurations get merged into the top level collection,
      as described in :doc:`the contexts documentation </concepts/contexts>`,
      and the final result forms the basis of the overall configuration setup.
    * Since the root collection is loaded at runtime, configuration options
      modifying the load process itself obviously won't take effect if defined
      at this level.

* **System-level configuration file** stored in ``/etc/``, such as
  ``/etc/invoke.yaml``. (See :ref:`config-files` for details on this and the
  other config-file entries.)
* **User-level configuration file** found in the running user's home directory,
  e.g. ``~/.invoke.yaml``.
* **Project-level configuration file** living next to your top level
  ``tasks.py``. For example, if your run of Invoke loads
  ``/home/user/myproject/tasks.py`` (see :doc:`our docs on the load
  process </concepts/loading>`), this might be
  ``/home/user/myproject/invoke.yaml``.
* **Environment variables** found in the invoking shell environment.

    * These aren't as strongly hierarchical as the rest, nor is the shell
      environment namespace owned wholly by Invoke, so we must rely on slightly
      verbose prefixing instead - see :ref:`env-vars` for details.

* **Runtime configuration file** whose path is given to :option:`-f`, e.g.
  ``inv -f /random/path/to/config_file.yaml``.
* **Command-line flags**, either dedicated ones for core options (like
  :option:`-e`) or use of :option:`--set` which allows runtime overriding of
  arbitrary configuration paths.


.. _config-files:

Configuration files
===================

blah blah multiple variants only one is chosen etc etc


.. _env-vars:

Environment variables
=====================

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
