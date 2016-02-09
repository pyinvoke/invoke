=========
Changelog
=========

* :support:`319 backported` Fixed an issue resulting from :issue:`255` which
  caused problems with how we generate release wheels (notably, some releases
  such as 0.12.1 fail when installing from wheels on Python 2).

  .. note::
    As part of this fix, the next release will distribute individual Python 2
    and Python 3 wheels instead of one 'universal' wheel. This change should be
    transparent to users.

  Thanks to ``@ojos`` for the initial report and Frazer McLean for some
  particularly useful feedback.
* :release:`0.12.2 <2016-02-07>`
* :support:`314 backported` (Partial fix.) Update ``MANIFEST.in`` so source
  distributions include some missing project-management files (e.g. our
  internal ``tasks.py``). This makes unpacked sdists more useful for things
  like running the doc or build tasks.
* :bug:`303` Make sure `~invoke.run` waits for its IO worker threads to cleanly
  exit (such as allowing a ``finally`` block to revert TTY settings) when
  ``KeyboardInterrupt`` (or similar) aborts execution in the main thread.
  Thanks to Tony S Yu and Máté Farkas for the report.
* :release:`0.12.1 <2016-02-03>`
* :bug:`308` Earlier changes to TTY detection & its use in determining features
  such as stdin pass-through, were insufficient to handle edge cases such as
  nested Invoke sessions or piped stdin to Invoke processes. This manifested as
  hangs and ``OSError`` messages about broken pipes.

  The issue has been fixed by overhauling all related code to use more specific
  and accurate checks (e.g. examining just ``fileno`` and/or just ``isatty``).

  Thanks to Tuukka Mustonen and Máté Farkas for the report (and for enduring
  the subsequent flood of the project maintainer's stream-of-consciousness
  ticket updates).
* :bug:`305` (also :issue:`306`) Fix up some test-suite issues causing failures
  on Windows/Appveyor. Thanks to Paul Moore.
* :bug:`289` Handful of issues, all fallout from :issue:`289`, which failed to
  make it out the door for 0.12.0. More are on the way but these should address
  blockers for some users:

    * Windows support for the new stdin replication functionality (this was
      totally blocking Windows users, as reported in :issue:`302` - sorry!);
    * Stdin is now mirrored to stdout when no PTY is present, so you can see
      what you're typing (plus a new `~invoke.runners.Runner.run` option and
      config param, ``echo_stdin``, allowing user override of this behavior);
    * Exposed the stdin read loop's sleep time as `Runner.input_sleep
      <invoke.runners.Runner.input_sleep>`;
    * Sped up some tests a bit.

* :release:`0.12.0 <2016-01-12>`
* :bug:`257 major` Fix a RecursionError under Python 3 due to lack of
  ``__deepcopy__`` on `~invoke.tasks.Call` objects. Thanks to Markus
  Zapke-Gründemann for initial report and Máté Farkas for the patch.
* :support:`265` Update our Travis config to select its newer build
  infrastructure and also run on PyPy3. Thanks to Omer Katz.
* :support:`254` Add an ``exclude`` option in our ``setup.py`` so setuptools
  doesn't try loading our vendored PyYAML's Python 2 sub-package under Python 3
  (or vice versa - though all reports were from Python 3 users). Thanks to
  ``@yoshiya0503`` for catch & initial patch.
* :feature:`68` Disable Python's bytecode caching by default, as it complicates
  our typical use case (frequently-changing .py files) and offers little
  benefit for human-facing startup times. Bytecode caching can be explicitly
  re-enabled by specifying ``--write-pyc`` at runtime. Thanks to Jochen Breuer
  for feature request and ``@brutus`` for initial patchset.
* :support:`144` Add code-coverage reporting to our CI builds (albeit `CodeCov
  <https://codecov.io>`_ instead of `coveralls.io <https://coveralls.io>`_).
  Includes rejiggering our project-specific coverage-generating tasks. Thanks
  to David Baumgold for the original request/PR and to Justin Abrahms for the
  tipoff re: CodeCov.
* :bug:`297 major` Ignore leading and trailing underscores when turning task
  arguments into CLI flag names.
* :bug:`296 major` Don't mutate ``sys.path`` on collection load if task's
  parent directory is already on ``sys.path``.
* :bug:`295 major` Make sure that `~invoke.run`'s ``hide=True`` also disables
  echoing. Otherwise, "hidden" helper ``run`` calls will still pollute output
  when run as e.g. ``invoke --echo ...``.
* :feature:`289` (also :issue:`263`) Implement :ref:`autoresponding
  <autoresponding>` for `~invoke.run`.
* :support:`-` Removed official Python 3.2 support; sibling projects also did
  this recently, it's simply not worth the annoyance given the userbase size.
* :feature:`228` (partial) Modified and expanded implementation of
  `~invoke.executor.Executor`, `~invoke.tasks.Task` and `~invoke.tasks.Call` to
  make implementing task parameterization easier.
* :support:`-` Removed the ``-H`` short flag, leaving just ``--hide``. This was
  done to avoid conflicts with Fabric's host-oriented ``-H`` flag. Favoritism
  is real! Apologies.

  .. warning:: This change is backwards compatible if you used ``-H``.

* :feature:`173` Overhauled top level CLI functionality to allow reusing
  Invoke for distinct binaries, optionally with bundled task namespaces as
  subcommands. As a side effect, this functionality is now much more extensible
  to boot. Thanks to Erich Heine for feedback/suggestions during development.

  .. warning::
    This change is backwards incompatible if you imported anything from the
    ``invoke.cli`` module (which is now rearchitected as
    `~invoke.program.Program`). It should be transparent to everybody else.

  .. seealso:: :ref:`reusing-as-a-binary`

* :bug:`- major` Fixed a bug in the parser where ``invoke --takes-optional-arg
  avalue --anotherflag`` was incorrectly considering ``--anotherflag`` to be an
  ambiguity error (as if ``avalue`` had not been given to
  ``--takes-optional-arg``.
* :release:`0.11.1 <2015-09-07>`
* :support:`- backported` Fix incorrect changelog URL in package metadata.
* :release:`0.11.0 <2015-09-07>`
* :feature:`-` Create `invoke.runners.Result.command` to preserve the command
  executed for post-execution introspection.
* :feature:`-` Detect local controlling terminal size
  (`~invoke.platform.pty_size`) and apply that information when creating
  pseudoterminals in `~invoke.run` when ``pty=True``.
* :bug:`- major` Display stdout instead of stderr in the ``repr()`` of
  `~invoke.exceptions.Failure` objects, when a pseudo-terminal was used.
  Previously, failure display focused on the stderr stream, which is always
  empty under pseudo-terminals.
* :bug:`- major` Correctly handle situations where `sys.stdin` has been
  replaced with an object lacking ``.fileno`` (e.g., some advanced Python
  shells, headless code execution tools, etc). Previously, this situation
  resulted in an ``AttributeError``.
* :bug:`- major` Capture & reraise exceptions generated by command execution I/O
  threads, in the main thread, as a `~invoke.exceptions.ThreadException`.
* :feature:`235` Allow custom stream objects to be used in `~invoke.run` calls,
  to be used instead of the defaults of ``sys.stdout``/``sys.stderr``.

  .. warning::
    This change required a major cleanup/rearchitecture of the command
    execution implementation. The vendored ``pexpect`` module has been
    completely removed and the API of the `~invoke.runners.Runner` class has
    changed dramatically (though **the API for run() itself has not**).

    Be aware there may be edge-case terminal behaviors which have changed or
    broken as a result of removing ``pexpect``. Please report these as bugs! We
    expect to crib small bits of what ``pexpect`` does but need concrete test
    cases first.

* :bug:`234 major` (also :issue:`243`) Preserve task-module load location when
  creating explicit collections with
  `~invoke.collection.Collection.from_module`; when this was not done,
  project-local config files were not loading correctly. Thanks to ``@brutus``
  and Jan Willems for initial report & troubleshooting, and to Greg Back for
  identifying the fix.
* :bug:`237 major` Completion output lacked "inverse" flag names (e.g.
  ``--no-myoption`` as a boolean negative version of a defaulting-to-True
  boolean ``myoption``). This has been corrected.
* :bug:`239 major` Completion erroneously presented core flags instead of
  per-task flags when both are present in the invocation being completed (e.g.
  ``inv --debug my_task -<tab>``). This has been fixed.
* :bug:`238 major` (partial fix) Update the ``zsh`` completion script to
  account for use of the ``--collection`` core flag.
* :support:`-` Additional rearranging of ``run``/``Runner`` related concerns
  for improved subclassing, organization, and use in other libraries,
  including:

    * Changed the name of the ``runner`` module to ``runners``.
    * Moved the top level ``run`` function from its original home in
      ``invoke.runner`` to `invoke.__init__ <invoke>`, to reflect the fact that
      it's now simply a convenience wrapper around ``Runner``.
    * Tweaked the implementation of `~invoke.runners.Runner` so it can
      reference `~invoke.context.Context` objects (useful for anticipated
      subclasses).

  .. warning::
    These are backwards incompatible changes if your code was doing any imports
    from the ``invoke.runner`` module (including especially
    ``invoke.runner.run``, which is now only ``invoke.run``). Function
    signatures have **not** changed.

* :support:`224` Add a completion script for the ``fish`` shell, courtesy of
  Jaime Marquínez Ferrándiz.
* :release:`0.10.1 <2015-03-17>`
* :support:`- backported` Tweak README to reflect recent(-ish) changes in
  ``pip`` re: users who install the development version via ``pip`` instead of
  using git.
* :release:`0.10.0 <2015-03-17>`
* :feature:`104` Add core CLI flag ``--complete`` to support shell tab
  completion scripts, and add some 'blessed' such scripts for bash (3 and 4)
  and zsh. Thanks to Ivan Malison and Andrew Roberts for providing discussion &
  early patchsets.
* :support:`-` Reorganize `~invoke.runners.Runner`, `~invoke.runners.Local` and
  ``invoke.runner.run`` for improved distribution of responsibilities &
  downstream subclassing.

  .. warning::
    This includes backwards incompatible changes to the API signature of most
    members of the ``invoke.runner`` module, including ``invoke.runner.run``.
    (However, in the case of ``invoke.runner.run``, the changes are mostly in
    the later, optional keyword arguments.)

* :feature:`219` Fall back to non-PTY command execution in situations where
  ``pty=True`` but no PTY appears present. See `~invoke.runners.Local` for
  details.
* :support:`212` Implement basic linting support using ``flake8``, and apply
  formatting changes to satisfy said linting. As part of this shakeup, also
  changed all old-style (``%s``) string formatting to new-style (``{0}``).
  Thanks to Collin Anderson for the foundational patch.
* :support:`215` (also :issue:`213`, :issue:`214`) Tweak tests & configuration
  sections of the code to include Windows compatibility. Thanks to Paul Moore.
* :bug:`201 major` (also :issue:`211`) Replace the old, first-draft gross
  monkeypatched Popen code used for ``invoke.runner.run`` with a
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
    The top level ``invoke.runner.run`` function has had a minor signature
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

* :bug:`191 major` Bypass ``pexpect``'s automatic command splitting to avoid
  issues running complex nested/quoted commands under a pty. Credit to
  ``@mijikai`` for noticing the problem.
* :bug:`183 major` Task docstrings whose first line started on the same line as
  the opening quote(s) were incorrectly presented in ``invoke --help <task>``.
  This has been fixed by using `inspect.getdoc`. Thanks to Pekka Klärck for the
  catch & suggested fix.
* :bug:`180 major` Empty invocation (e.g. just ``invoke`` with no flags or
  tasks, and when no default task is defined) no longer printed help output,
  instead complaining about the lack of default task. It now prints help again.
  Thanks to Brent O'Connor for the catch.
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

* :support:`-` Refactor the `invoke.runners.Runner` module to differentiate
  what it means to run a command in the abstract, from execution specifics. Top
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
