=======
``cli``
=======

.. seealso::
    This page documents the ``invoke`` command-line program itself. For
    background on how parsing works, please see :doc:`/concepts/cli`. For
    details on task execution, see :doc:`/concepts/execution`.


``inv[oke]`` command-line program
=================================

One of the main ways to use Invoke is via its command-line program, which can
load task modules and execute their tasks, optionally with flags for
parameterization.

.. TODO: autodoc-like ext that spits out option nodes automatically

``invoke``'s usage looks like::

    $ inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

The core options (which must be given before any task names) are as follows:

.. option:: --complete

    Print (line-separated) valid tab-completion options for an Invoke command
    line given as the 'remainder' (i.e. after a `--`). Used for building shell
    completion scripts.

    For example, when the local tasks tree contains tasks named ``foo`` and
    ``bar``, and when ``foo`` takes flags ``--foo-arg`` and ``--foo-arg-2``,
    you might use it like this::

        # Empty input: just task names
        $ inv --complete --
        foo
        bar

        # Input not ending with a dash: task names still
        $ inv --complete -- foo --foo-arg
        foo
        bar

        # Input ending with a dash: current context's flag names
        $ inv --complete -- foo -
        --foo-arg
        --foo-arg-2

    For more details on how to use this option, see the bundled completion
    scripts stored in ``completion/`` in the source distribution.

.. option:: --no-dedupe

    Disable task deduplication.

.. option:: -c STRING, --collection=STRING

    Specify collection name to load.

.. option:: -d, --debug

    Enable debug output.

.. option:: -e, --echo

    Echo executed commands before running. Requires :doc:`contextualized tasks
    </concepts/context>`.

.. option:: -f, --config

    Specify a :ref:`runtime configuration file <config-hierarchy>` to load.

.. option:: -h STRING, --help=STRING

    Show core or per-task help and exit.

.. option:: -H STRING, --hide=STRING

    Set default value of run()'s 'hide' kwarg.

.. option:: -l, --list

    List available tasks.

.. option:: -p, --pty

    Use a pty when executing shell commands. Requires :doc:`contextualized
    tasks </concepts/context>`.

.. option:: -r STRING, --root=STRING

    Change root directory used for finding task modules.

.. option:: -V, --version

    Show version and exit.

.. option:: -w, --warn-only

    Warn, instead of failing, when shell commands fail. Requires
    :doc:`contextualized tasks </concepts/context>`.


The internal ``cli`` module's API docs
======================================

Potentially useful if you need to make your own command-line tool instead of
using ``invoke`` directly.

.. automodule:: invoke.cli
