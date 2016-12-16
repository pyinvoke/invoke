.. _inv:

========================
``inv[oke]`` core usage 
========================

.. seealso::
    This page documents ``invoke``'s core arguments, options and behavior. For
    details on invoking user-specified tasks, see
    :doc:`/concepts/invoking-tasks`.


Core options and flags
======================

``invoke``'s usage looks like::

    $ inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

All core options & flags are below; almost all of them must be given *before*
any task names, with a few (such as :option:`--help`) being specially looked
for anywhere in the command line.

.. option:: --complete

    Print (line-separated) valid tab-completion options for an Invoke command
    line given as the 'remainder' (i.e. after a ``--``). Used for building
    :ref:`shell completion scripts <tab-completion>`.

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

    For more details on how to make best use of this option, see the
    print-completion-script option below.

.. option:: --print-completion-script=STRING

    Print a completion script for the console type you prefer (bash, zsh or
    fish). This can be sourced into the current session in order to enjoy
    :ref:`tab-completion for tasks and options <tab-completion>`.

.. option:: --hide=STRING

    Set default value of run()'s 'hide' kwarg.

.. option:: --no-dedupe

    Disable task deduplication.

.. _prompt-for-sudo-password:

.. option:: --prompt-for-sudo-password

    Prompt at the start of the session (before executing any tasks) for the
    ``sudo.password`` configuration value. This allows users who don't want to
    keep sensitive material in the config system or their shell environment to
    rely on user input, without otherwise interrupting the flow of the program.

.. option:: --write-pyc

    By default, Invoke disables bytecode caching as it can cause hard-to-debug
    problems with task files and (for the kinds of things Invoke is typically
    used for) offers no noticeable speed benefit. If you really want your
    ``.pyc`` files back, give this option.

.. option:: -c STRING, --collection=STRING

    Specify collection name to load.

.. option:: -d, --debug

    Enable debug output.

.. option:: -e, --echo

    Echo executed commands before running.

.. option:: -f, --config

    Specify a :ref:`runtime configuration file <config-hierarchy>` to load.

    Note that you may instead use the ``INVOKE_RUNTIME_CONFIG`` environment
    variable in place of this option. If both are given, the CLI option will
    win out.

.. option:: -h STRING, --help=STRING

    When given without any task names, displays core help; when given with a
    task name (may come before *or* after the task name) displays help for that
    particular task.

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

      - ``name``: String name of collection; for the root collection this is
        typically the module name, so unless you're supplying alternate
        collection name to the load process, it's usually ``"tasks"`` (from
        ``tasks.py``.)
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


.. _tab-completion:

Shell tab completion
====================

Invoke's philosophy is to implement generic APIs and then "bake in" a few
common use cases built on top of those APIs, and tab completion is no
different. Generic tab completion functionality is provided by the
:option:`--complete` core CLI option described above, and we distribute a
handful of ready-made wrapper scripts aimed at the most common shells such as
``bash`` and ``zsh`` (plus others). To use one of these scripts:

* ``source`` the shell completion helper script provided by Invoke into your
  current session::

        $ source <(invoke --print-completion-script bash)
        
  or::

        $ source <(invoke --print-completion-script zsh)
 
  ..

    * The line above is probably most useful if you place it in your shell 
      login file (i.e. ``~/.bash_profile`` or ``~/.zshrc``).    
    * If your program uses :ref:`a distinct binary name <reusing-as-a-binary>`,
      substitute that for ``invoke`` in the command above and in the guide
      below.
    * Specifying ``fish`` as console type (instead of ``bash`` or
      ``zsh``) is supported, but is currently not suitable to be sourced.
      Copy the output of ``invoke --print-completion-script fish``
      into a file in your ``~/.config/fish/completions`` directory.

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
