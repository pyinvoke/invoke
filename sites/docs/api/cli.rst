=======================
``cli``: CLI entrypoint
=======================

``inv[oke]`` command-line program
=================================

One of the main ways to use Invoke is via its command-line program, which can
load task modules and execute their tasks, optionally with flags for
parameterization.

.. TODO: autodoc-like ext that spits out option nodes automatically

``invoke``'s usage looks like::

    $ inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

The core options (which must be given before any task names) are as follows:

.. option:: --no-dedupe

    Disable task deduplication.

.. option:: -c STRING, --collection=STRING

    Specify collection name to load.

.. option:: -d, --debug

    Enable debug output.

.. option:: -e, --echo

    Echo executed commands before running.

.. option:: -h STRING, --help=STRING

    Show core or per-task help and exit.

.. option:: -H STRING, --hide=STRING

    Set default value of run()'s 'hide' kwarg.

.. option:: -l, --list

    List available tasks.

.. option:: -p, --pty

    Use a pty when executing shell commands.

.. option:: -r STRING, --root=STRING

    Change root directory used for finding task modules.

.. option:: -V, --version

    Show version and exit.

.. option:: -w, --warn-only

    Warn, instead of failing, when shell commands fail.


.. seealso::
    * :doc:`/concepts/cli` - for background on how parsing works
    * :doc:`/concepts/execution` - for details on how tasks get executed


The internal ``cli`` module's API docs
======================================

Potentially useful if you need to make your own command-line tool instead of
using ``invoke`` directly.

.. automodule:: invoke.cli
