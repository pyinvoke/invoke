=========
Changelog
=========

* :bug:`201 major` (also :issue:`211`) Replace the old, first-draft gross
  monkeypatched Popen code used for `~invoke.runner.run` with a
  non-monkeypatched approach that works better on non-POSIX platforms like
  Windows, and also attempts to handle encoding and locale issues more
  gracefully (meaning: at all gracefully).

  Specifically, the new approach uses threading instead of ``select.select``,
  and performs explicit encoding/decoding based on detected or explicitly
  expressed encodings.

  Major thanks to Paul Moore for an enormous amount of
  testing/experimentation/discussion, as well as the bulk of the code changes
  themselves.

  .. warning::
    The top level `~invoke.runner.run` function has had a minor signature
    change: the sixth positional argument used to be ``runner`` and is now
    ``encoding`` (with ``runner`` now being the seventh positional argument).

* :feature:`147` Drastically overhaul/expand the configuration system to
  account for multiple configuration levels including (but not limited to) file
  paths, environment variables, and Python-level constructs (previously the
  only option). See :ref:`configuration` for details. Thanks to Erich Heine for
  his copious feedback on this topic.

  .. warning::
    This is technically a backwards incompatible change, though some existing
    user config-setting code may continue to work as-is. In addition, this
    system may see further updates before 1.0.

* :bug:`191` Bypass ``pexpect``'s automatic command splitting to avoid issues
  running complex nested/quoted commands under a pty. Credit to ``@mijikai``
  for noticing the problem.
* :bug:`183` Task docstrings whose first line started on the same line as the
  opening quote(s) were incorrectly presented in ``invoke --help <task>``. This
  has been fixed by using `inspect.getdoc`. Thanks to Pekka Klärck for the
  catch & suggested fix.
* :bug:`180` Empty invocation (e.g. just ``invoke`` with no flags or tasks, and
  when no default task is defined) no
  longer printed help output, instead complaining about the lack of default
  task. It now prints help again. Thanks to Brent O'Connor for the catch.
* :bug:`175 major` ``autoprint`` did not function correctly for tasks stored
  in sub-collections; this has been fixed. Credit: Matthias Lehmann.
* :release:`0.9.0 <2014-08-26>`
* :bug:`165 major` Running ``inv[oke]`` with no task names on a collection
  containing a default task should (intuitively) have run that default task,
  but instead did nothing. This has been fixed.
* :bug:`167 major` Running the same task multiple times in one CLI session was
  horribly broken; it works now. Thanks to Erich Heine for the report.
* :bug:`119 major` (also :issue:`162`, :issue:`113`) Better handle
  platform-sensitive operations such as pty size detection or use, either
  replacing with platform-specific implementations or raising useful
  exceptions. Thanks to Gabi Davar and (especially) Paul Moore, for feedback &
  original versions of the final patchset.
* :feature:`136` Added the ``autoprint`` flag to
  `invoke.tasks.Task`/`@task <invoke.tasks.task>`, allowing users to set up
  tasks which act as both subroutines & "print a result" CLI tasks. Thanks to
  Matthias Lehmann for the original patch.
* :bug:`162 major` Adjust platform-sensitive imports so Windows users don't
  encounter import-time exceptions. Thanks to Paul Moore for the patch.
* :support:`169` Overhaul the Sphinx docs into two trees, one for main project
  info and one for versioned API docs.
* :bug:`- major` Fixed a sub-case of the already-mostly-fixed :issue:`149` so
  the error message works usefully even with no explicit collection name given.
* :release:`0.8.2 <2014-06-15>`
* :bug:`149` Print a useful message to stderr when Invoke can't find the
  requested collection/tasks file, instead of displaying a traceback.
* :bug:`145` Ensure a useful message is displayed (instead of a confusing
  exception) when listing empty task collections.
* :bug:`142` The refactored Loader class failed to account for the behavior of
  `imp.find_module` when run against packages (vs modules) and was exploding at
  load time. This has been fixed. Thanks to David Baumgold for catch & patch.
* :release:`0.8.1 <2014-06-09>`
* :bug:`140` Revert incorrect changes to our ``setup.py`` regarding detection
  of sub-packages such as the vendor tree & the parser. Also add additional
  scripting to our Travis-CI config to catch this class of error in future.
  Thanks to Steven Loria and James Cox for the reports.
* :release:`0.8.0 <2014-06-08>`
* :feature:`135` (also bugs :issue:`120`, :issue:`123`) Implement post-tasks to
  match pre-tasks, and allow control over the arguments passed to both (via
  `invoke.tasks.call`). For details, see :ref:`pre-post-tasks`.

  .. warning::
      Pre-tasks were overhauled a moderate amount to implement this feature;
      they now require references to **task objects** instead of **task
      names**. This is a backwards incompatible change.

* :support:`25` Trim a bunch of time off the test suite by using mocking and
  other tools instead of dogfooding a bunch of subprocess spawns.
* :bug:`128 major` Positional arguments containing underscores were not
  exporting to the parser correctly; this has been fixed. Thanks to J. Javier
  Maestro for catch & patch.
* :bug:`121 major` Add missing help output denoting inverse Boolean options
  (i.e. ``--[no-]foo`` for a ``--foo`` flag whose value defaults to true.)
  Thanks to Andrew Roberts for catch & patch.
* :support:`118` Update the bundled ``six`` plus other minor tweaks to support
  files. Thanks to Matt Iversen.
* :feature:`115` Make it easier to reuse Invoke's primary CLI machinery in
  other (non-Invoke-distributed) bin-scripts. Thanks to Noah Kantrowitz.
* :feature:`110` Add task docstrings' 1st lines to ``--list`` output. Thanks to
  Hiroki Kiyohara for the original PR (with assists from Robert Read and James
  Thigpen.)
* :support:`117` Tidy up ``setup.py`` a bit, including axing the (broken)
  `distutils` support. Thanks to Matt Iversen for the original PR & followup
  discussion.
* :feature:`87` (also :issue:`92`) Rework the loader module such that recursive
  filesystem searching is implemented, and is used instead of searching
  `sys.path`.
  
  This adds the behavior most users expect or are familiar with from Fabric 1
  or similar tools; and it avoids nasty surprise collisions with other
  installed packages containing files named ``tasks.py``.

  Thanks to Michael Hahn for the original report & PR, and to Matt Iversen for
  providing the discovery algorithm used in the final version of this change.

  .. warning::
      This is technically a backwards incompatible change (reminder: we're not
      at 1.0 yet!). You'll only notice if you were relying on adding your tasks
      module to ``sys.path`` and then calling Invoke elsewhere on the
      filesystem.

* :support:`-` Refactor the `invoke.runner.Runner` module to differentiate what
  it means to run a command in the abstract, from execution specifics. Top
  level API is unaffected.
* :bug:`131 major` Make sure one's local tasks module is always first in
  ``sys.path``, even if its parent directory was already somewhere else in
  ``sys.path``. This ensures that local tasks modules never become hidden by
  third-party ones. Thanks to ``@crccheck`` for the early report and to Dorian
  Puła for assistance fixing.
* :bug:`116 major` Ensure nested config overrides play nicely with default
  tasks and pre-tasks.
* :bug:`127 major` Fill in tasks' exposed ``name`` attribute with body name if
  explicit name not given.
* :feature:`124` Add a ``--debug`` flag to the core parser to enable easier
  debugging (on top of existing ``INVOKE_DEBUG`` env var.)
* :feature:`125` Improve output of Failure exceptions when printed.
* :release:`0.7.0 <2014.01.28>`
* :feature:`109` Add a ``default`` kwarg to
  `invoke.collection.Collection.add_task` allowing per-collection control over
  default tasks.
* :feature:`108` Update `invoke.collection.Collection.from_module` to accept
  useful shorthand arguments for tweaking the `invoke.collection.Collection`
  objects it creates (e.g. name, configuration.)
* :feature:`107` Update configuration merging behavior for more flexible reuse
  of imported task modules, such as parameterizing multiple copies of a module
  within a task tree.
* :release:`0.6.1 <2013.11.21>`
* :bug:`96` Tasks in subcollections which set explicit names (via e.g.
  ``@task(name='foo')``) were not having those names honored. This is fixed.
  Thanks to Omer Katz for the report.
* :bug:`98` **BACKWARDS INCOMPATIBLE CHANGE!** Configuration merging has been
  reversed so outer collections' config settings override inner collections.
  This makes distributing reusable modules significantly less silly.
* :release:`0.6.0 <2013.11.21>`
* :bug:`86 major` Task arguments named with an underscore broke the help feature;
  this is now fixed. Thanks to Stéphane Klein for the catch.
* :feature:`89` Implemented configuration for distributed task modules: can set
  config options in `invoke.collection.Collection` objects and they are made
  available to contextualized tasks.
* :release:`0.5.1 <2013.09.15>`
* :bug:`81` Fall back to sane defaults for PTY sizes when autodetection gives
  insane results. Thanks to ``@akitada`` for the patch.
* :bug:`83` Fix a bug preventing underscored keyword arguments from working
  correctly as CLI flags (e.g. ``mytask --my-arg`` would not map back correctly
  to ``mytask(my_arg=...)``.) Credit: ``@akitada``.
* :release:`0.5.0 <2013.08.16>`
* :feature:`57` Optional-value flags added - e.g. ``--foo`` tells the parser to
  set the ``foo`` option value to True; ``--foo myval`` sets the value to
  "myval". The built-in ``--help`` option now leverages this feature for
  per-task help (e.g. ``--help`` displays global help, ``--help mytask``
  displays help for ``mytask`` only.)
* :bug:`55 major` A bug in our vendored copy of ``pexpect`` clashed with a
  Python 2->3 change in import behavior to prevent Invoke from running on
  Python 3 unless the ``six`` module was installed in one's environment. This
  was fixed - our vendored ``pexpect`` now always loads its sibling vendored
  ``six`` correctly.
