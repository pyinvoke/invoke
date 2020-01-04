.. _inv:

========================
``inv[oke]`` core usage
========================

.. seealso::
    This page documents ``invoke``'s core arguments, options and behavior
    (which includes options present in :ref:`custom Invoke-based binaries
    <reusing-as-a-binary>`). For details on invoking user-specified tasks and
    other parser-related details, see :doc:`/concepts/invoking-tasks`.


Core options and flags
======================

``invoke``'s usage looks like::

    $ inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

All core options & flags are below; almost all of them must be given *before*
any task names, with a few (such as :option:`--help`) being specially looked
for anywhere in the command line. (For parsing details, see
:ref:`basic-cli-layout`.)

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

    For more details on how to make best use of this option, see
    :option:`--print-completion-script`.

.. option:: --hide=STRING

    Set default value of run()'s 'hide' kwarg.

.. option:: --no-dedupe

    Disable task deduplication.

.. _print-completion-script:

.. option:: --print-completion-script=SHELL

    Print a completion script for desired ``SHELL`` (e.g. ``bash``, ``zsh``,
    etc). This can be sourced into the current session in order to enjoy
    :ref:`tab-completion for tasks and options <tab-completion>`.

    These scripts are bundled with Invoke's distributed codebase, and
    internally make use of :option:`--complete`.

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

.. option:: --dry

    Echo commands instead of actually running them; specifically, causes any
    ``run`` calls to:

    - Act as if the ``echo`` option has been turned on, printing the
      command-to-be-run to stdout;
    - Skip actual subprocess invocation (returning before any of that machinery
      starts running);
    - Return a dummy `~invoke.runners.Result` object with 'blank' values (empty
      stdout/err strings, ``0`` exit code, etc).

.. option:: -D, --list-depth=INT

    Limit :option:`--list` display to the specified number of levels, e.g.
    ``--list-depth 1`` to show only top-level tasks and namespaces.

    If an argument is given to ``--list``, then this depth is relative; so
    ``--list build --list-depth 1`` shows everything at the top level of the
    ``build`` subtree.

    Default behavior if this is not given is to show all levels of the entire
    task tree.

.. option:: -e, --echo

    Echo executed commands before running.

.. option:: -f, --config

    Specify a :ref:`runtime configuration file <config-hierarchy>` to load.

    Note that you may instead use the ``INVOKE_RUNTIME_CONFIG`` environment
    variable in place of this option. If both are given, the CLI option will
    win out.

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

.. option:: -h STRING, --help=STRING

    When given without any task names, displays core help; when given with a
    task name (may come before *or* after the task name) displays help for that
    particular task.

.. option:: -l, --list=STRING

    List available tasks. Shows all tasks by default; may give an explicit
    namespace to 'root' the displayed task tree to only that namespace. (This
    argument may contain periods, as with task names, so it's possible to show
    only a small, deep portion of the overall tree if desired.)

.. option:: -p, --pty

    Use a pty when executing shell commands.

.. option:: -r STRING, --search-root=STRING

    Change root directory used for finding task modules.

.. option:: -T INT, --command-timeout=INT

    Set a default command execution timeout of INT seconds. Maps to the
    ``timeouts.command`` config setting.

.. option:: -V, --version

    Show version and exit.

.. option:: -w, --warn-only

    Warn, instead of failing, when shell commands fail.


.. _tab-completion:

Shell tab completion
====================

Generating a completion script
------------------------------

Invoke's philosophy is to implement generic APIs and then "bake in" a few
common use cases built on top of those APIs; tab completion is no different.
Generic tab completion functionality (outputting a shell-compatible list of
completion tokens for a given command line context) is provided by the
:option:`--complete` core CLI option described above.

However, you probably won't need to use that flag yourself: we distribute a
handful of ready-made wrapper scripts aimed at the most common shells like
``bash`` and ``zsh`` (plus others). These scripts can be automatically
generated from Invoke or :ref:`any Invoke-driven command-line tool
<reusing-as-a-binary>`, using :option:`--print-completion-script`; the printed
scripts will contain the correct binary name(s) for the program generating
them.

For example, the following command prints (to stdout) a script which works for
``zsh``, instructs ``zsh`` to use it for the ``inv`` and ``invoke`` programs,
and calls ``invoke --complete`` at runtime to get dynamic completion
information::

    $ invoke --print-completion-script zsh

.. note::
    You'll probably want to source this command or store its output somewhere
    permanently; more on that in the next section.

Similarly, the `Fabric <http://fabfile.org>`_ tool inherits from Invoke, and
only has a single binary name (``fab``); if you wanted to get Fabric completion
in ``bash``, you would say::

    $ fab --print-completion-script bash

In the rest of this section, we'll use ``inv`` in examples, but please remember
to replace it with the program you're actually using, if it's not Invoke
itself!

Sourcing the script
-------------------

There are a few ways to utilize the output of the above commands, depending on
your needs, where the program is installed, and your shell:

- The simplest and least disruptive method is to ``source`` the printed
  completion script inline, which doesn't place anything on disk, and will only
  affect the current shell session::

    $ source <(inv --print-completion-script zsh)

- If you've got the program available in your system's global Python
  interpreter (and you're okay with running the program at the startup of each
  shell session - Python's speed is admittedly not its strong point) you could
  add that snippet to your shell's startup file, such as ``~/.zshrc`` or
  ``~/.bashrc``.
- If the program's available globally but you'd prefer to *avoid* running an
  extra Python program at shell startup, you can cache the output of the
  command in its own file; where this file lives is entirely up to you and how
  your shell is configured. For example, you might just drop it into your home
  directory as a hidden file::

    $ inv --print-completion-script zsh > ~/.invoke-completion.sh

  and then perhaps add the following to the end of ``~/.zshrc``::

    source ~/.invoke-completion.sh

  But again, this is entirely up to you and your shell.

  .. note::
    If you're using ``fish``, you *must* use this tactic, as our fish
    completion script is not suitable for direct sourcing. Fish shell users
    should direct the output of the command to a file in the
    ``~/.config/fish/completions/`` directory.

- Finally, if your copy of the needing-completion program is only installed in
  a specific environment like a virtualenv, you can use either of the above
  techniques:

    - Caching the output and referencing it in a global shell startup file will
      still work in this case, as it does not require the program to be
      available when the shell loads -- only when you actually attempt to tab
      complete.
    - Using the ``source <(inv --print-completion-script yourshell)`` approach
      will work *as long as* you place it in some appropriate per-environment
      startup file, which will vary depending on how you manage Python
      environments. For example, if you use ``virtualenvwrapper``, you could
      append the ``source`` line in ``/path/to/virtualenv/bin/postactivate``.

Utilizing tab completion itself
-------------------------------

You've ensured that the completion script is active in your environment - what
have you gained?

- By default, tabbing after typing ``inv`` or ``invoke`` will display task
  names from your current directory/project's tasks file.
- Tabbing after typing a dash (``-``) or double dash (``--``) will display
  valid options/flags for the current context: core Invoke options if no task
  names have been typed yet; options for the most recently typed task
  otherwise.

    - Tabbing while typing a partial long option will complete matching long
      options, using your shell's native substring completion. E.g. if no task
      names have been typed yet, ``--e<tab>`` will offer ``--echo`` as a
      completion option.

- Hitting tab when the most recent typed/completed token is a flag which takes
  a value, will 'fall through' to your shell's native filename completion.

    - For example, prior to typing a task name, ``--config <tab>`` will
      complete local file paths to assist in filling in a config file.
