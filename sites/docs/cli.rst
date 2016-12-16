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


.. _tab-completion:

Shell tab completion
====================

Invoke ships with some shell completion scripts. If you're 
using Bash or Zsh, simply do the following:

* ``source`` the shell completion helper script provided by Invoke into
  your current session::

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
