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
    argument may contain periods, as with task names, so it's possible to show
    only a small, deep portion of the overall tree if desired.)

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
      names.
    - ``nested``: a nested (4-space indented) vertical list, where each level
      implicitly includes its parent (with leading dots as a strong visual clue
      that these are still subcollection tasks.)
    - ``json``: intended for consumption by scripts or other programs, this
      format emits JSON representing the task tree, with each 'node' in the
      tree (the outermost document being the root node, and thus a JSON object)
      consisting of the following keys:

      - ``name``: String name of collection; the root collection's "name" is
        null.
      - ``help``: First line of collection's docstring, if it came from a
        module; null otherwise (or if module lacked a docstring.)
      - ``tasks``: Immediate children of this collection; an array of objects
        of the following form:

        - ``name``: Task's local name within its collection (i.e. not the full
          dotted path you might see with the ``flat`` format; reconstructing
          that path is left up to the consumer.)
        - ``help``: First line of task's docstring, or null if it had none.
        - ``aliases``: An array of string aliases for this task.

      - ``default``: String naming which task within this collection, if any,
        is the default task. Is null if no task is the default.
      - ``collections``: An array of any sub-collections within this
        collection, members of which which will have the same structure as this
        outermost document, recursively.

      The JSON emitted is not pretty-printed, but does end with a trailing
      newline.

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
