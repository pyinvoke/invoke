.. _inv:

======================
Command-line interface
======================

.. seealso::
    This page documents the ``invoke`` command-line program itself. For
    background on how argument parsing works, please see :doc:`/concepts/cli`.
    For details on task execution, see :doc:`/concepts/execution`.


``inv[oke]`` command-line program
=================================

One of the main ways to use Invoke is via its command-line program, ``invoke``
(also available as the shorter name ``inv``), which can load task modules and
execute their tasks, optionally with flags for parameterization.

.. TODO: autodoc-like ext that spits out option nodes automatically

``invoke``'s usage looks like::

    $ inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

The core options (which must be given before any task names) are as follows:

.. option:: --complete

    Print (line-separated) valid tab-completion options for an Invoke command
    line given as the 'remainder' (i.e. after a ``--``). Used for building
    shell completion scripts.

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

.. option:: --hide=STRING

    Set default value of run()'s 'hide' kwarg.

.. option:: --no-dedupe

    Disable task deduplication.

.. option:: -c STRING, --collection=STRING

    Specify collection name to load.

.. option:: -d, --debug

    Enable debug output.

.. option:: -e, --echo

    Echo executed commands before running.

.. option:: -f, --config

    Specify a :ref:`runtime configuration file <config-hierarchy>` to load.

.. option:: -h STRING, --help=STRING

    Show core or per-task help and exit.

.. option:: -l, --list=STRING

    List available tasks. Shows all tasks by default; may give an explicit
    namespace to 'root' the displayed task tree to only that namespace. (This
    argument may contain periods, as with task names.)

.. option:: -D, --list-depth=INT

    Limit :option:`--list` display to the specified number of levels, e.g.
    ``--list-depth 1`` to show only top-level tasks and namespaces.

    If an argument is given to ``--list``, then this depth is relative; so
    ``--list build --list-depth 1`` shows everything at the top level of the
    ``build`` subtree.

    Default behavior if this is not given is to show all levels of the entire
    task tree.

.. option:: -F, --list-format=STRING

    Change the format used to display the output of :option:`--list`; may be
    one of:

    - ``flat`` (the default): single, flat vertical list with dotted task
      names, and docstrings in a second column.
    - ``nested``: a nested (4-space indented) vertical list without dotted task
      names. No docstrings are displayed.
    - ``json``: intended for consumption by scripts or other programs, this
      format emits (non-pretty-printed) JSON data representing the task tree,
      with each 'node' in the tree consisting of the following keys:

      - ``collection``: String name of collection; the root collection's "name"
        is null.
      - ``docstring``: Docstring of collection, if it came from a module; null
        otherwise.
      - ``tasks``: Immediate children of this collection; an array of string
        names.
      - ``collections``: Any sub-collections within this collection, of the
        same format.

.. option:: -p, --pty

    Use a pty when executing shell commands.

.. option:: -r STRING, --search-root=STRING

    Change root directory used for finding task modules.

.. option:: -V, --version

    Show version and exit.

.. option:: -w, --warn-only

    Warn, instead of failing, when shell commands fail.


Shell tab completion
====================

Invoke ships with some shell completion scripts, which leverage a core CLI
mechanism suitable for use in custom completion scripts as well. If you're
using Bash or Zsh, simply do the following:

* Obtain the source distribution, or visit the ``/completion/`` folder `on Github
  <https://github.com/pyinvoke/invoke/blob/master/completion/>`_, and place a
  copy of the appropriate file (e.g. ``/completion/bash`` for Bash users)
  somewhere on your local system.
* ``source`` the file in your shell login file (e.g. ``.bash_profile``,
  ``.zshrc``).
* By default, tabbing after typing ``inv`` or ``invoke`` will display task
  names from your current directory/project's tasks file.
* Tabbing after typing a dash (``-``) or double dash (``--``) will display
  valid options/flags for the current context: core Invoke options if no task
  names have been typed yet; options for the most recently typed task
  otherwise.

    * Tabbing while typing a partial long option will complete matching long
      options, using your shell's native substring completion. E.g. if no task
      names have been typed yet, ``--e<tab>`` will offer ``--echo`` as a
      completion option.

* Hitting tab when the most recent typed/completed token is a flag which takes
  a value, will 'fall through' to your shell's native filename completion.

    * For example, prior to typing a task name, ``--config <tab>`` will
      complete local file paths to assist in filling in a config file.
