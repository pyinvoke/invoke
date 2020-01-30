=========
Changelog
=========

- :release:`1.4.1 <2020-01-29>`
- :release:`1.3.1 <2020-01-29>`
- :support:`586` Explicitly strip out ``__pycache__`` (and for good measure,
  ``.py[co]``, which previously we only stripped from the ``tests/`` folder) in
  our ``MANIFEST.in``, since at least some earlier releases erroneously
  included such. Credit to Martijn Pieters for the report and Floris Lambrechts
  for the patch.
- :bug:`660` Fix an issue with `~invoke.run` & friends having intermittent
  problems at exit time (symptom was typically about the exit code value being
  ``None`` instead of an integer; often with an exception trace). Thanks to
  Frank Lazzarini for the report and to the numerous others who provided
  reproduction cases.
- :bug:`518` Close pseudoterminals opened by the `~invoke.runners.Local` class
  during ``run(..., pty=True)``. Previously, these were only closed
  incidentally at process shutdown, causing file descriptor leakage in
  long-running processes. Thanks to Jonathan Paulson for the report.
- :release:`1.4.0 <2020-01-03>`
- :bug:`637 major` A corner case in `~invoke.context.Context.run` caused
  overridden streams to be unused if those streams were also set to be hidden
  (eg ``run(command, hide=True, out_stream=StringIO())`` would result in no
  writes to the ``StringIO`` object).

  This has been fixed - hiding for a given stream is now ignored if that stream
  has been set to some non-``None`` (and in the case of ``in_stream``,
  non-``False``) value.
- :bug:`- major` As part of feature work on :issue:`682`, we noticed that the
  `~invoke.runners.Result` return value from `~invoke.context.Context.run` was
  inconsistent between dry-run and regular modes; for example, the dry-run
  version of the object lacked updated values for ``hide``, ``encoding`` and
  ``env``. This has been fixed.
- :feature:`682` (originally reported as :issue:`194`) Add asynchronous
  behavior to `~invoke.runners.Runner.run`:

  - Basic asynchronicity, where the method returns as soon as the subprocess
    has started running, and that return value is an object with methods
    allowing access to the final result.
  - "Disowning" subprocesses entirely, which not only returns immediately but
    also omits background threading, allowing the subprocesses to outlive
    Invoke's own process.

  See the updated API docs for the `~invoke.runners.Runner` for details on the
  new ``asynchronous`` and ``disown`` kwargs enabling this behavior. Thanks to
  ``@MinchinWeb`` for the original report.
- :feature:`-` Never accompanied the top-level singleton `~invoke.run` (which
  simply wraps an anonymous `~invoke.context.Context`'s ``run`` method) with
  its logical sibling, `~invoke.sudo` - this has been remedied.
- :release:`1.3.0 <2019-08-06>`
- :feature:`324` Add basic dry-run support, in the form of a new
  :option:`--dry` CLI option and matching ``run.dry`` config setting, which
  causes command runners (eg `~invoke.run`, `Context.run
  <invoke.context.Context.run>`) to:

  - Act as if the ``echo`` option has been turned on, printing the
    command-to-be-run to stdout;
  - Skip actual subprocess invocation (returning before any of that machinery
    starts running);
  - Return a dummy `~invoke.runners.Result` object with 'blank' values (empty
    stdout/err strings, ``0`` exit code, etc).

  This allows quickly seeing what a given task or series of tasks might do,
  without actually running any shell commands (though naturally, any
  state-modifying Python code will still run).

  Thanks to Monty Hindman for the feature request and ``@thebjorn`` for the
  initial patch.

- :bug:`384 major` (via :issue:`653`) Modify config file loading so it detects
  missing-file IOErrors via their ``errno`` attribute instead of their string
  rendering (eg ``"No such file"``). This should improve compatibility for
  non-English locales. Thanks to Patrick Massot for the report and Github user
  ``@cybiere`` for the patch.
- :feature:`539` (via :issue:`645`) Add support for command timeouts, i.e. the
  ability to add an upper bound on how long a call to
  `~invoke.context.Context.run` may take to execute. Specifically:

  - A ``timeout`` argument to `~invoke.context.Context.run`.
  - The ``timeouts.command`` config setting mapping to that argument.
  - The :option:`-T/--command-timeout <-T>` CLI flag.

  Thanks to Israel Fruchter for the request & an early version of the patchset.
- :bug:`552 major` (also :issue:`553`) Add a new `~invoke.runners.Runner`
  method, `~invoke.runners.Runner.close_proc_stdin`, and call it when standard
  input processing detects an EOF. Without this, subprocesses that read their
  stdin until EOF would block forever, hanging the program. Thanks to
  ``@plockc`` for the report & initial patch.

  .. note::
    This fix only applies when ``pty=False`` (the default); PTYs complicate the
    situation greatly (but also mean the issue is less likely to occur).

- :bug:`557` (with assist from :issue:`640`) Fix the
  `~invoke.context.Context.cd` and `~invoke.context.Context.prefix` context
  managers so that ``with cd`` and ``with prefix`` correctly revert their state
  manipulations after they exit, when exceptions occur. Thanks to Jon Walsh and
  Artur Puzio for their respective patches.
- :bug:`466 major` Update the parsing and CLI-program mechanisms so that all
  core arguments may be given within task CLI contexts; previously this
  functionality only worked for the ``--help`` flag, and other core arguments
  given after task names (such as ``--echo``) were silently ignored.
- :feature:`-` Allow the configuration system to override which
  `~invoke.executor.Executor` subclass to use when executing tasks (via an
  import-oriented string).

  Specifically, it's now possible to alter execution by distributing such a
  subclass alongside, for example, a repository-local config file which sets
  ``tasks.executor_class``; previously, this sort of thing required use of
  :ref:`custom binaries <reusing-as-a-binary>`.
- :release:`1.2.0 <2018-09-13>`
- :feature:`301` (via :issue:`414`) Overhaul tab completion mechanisms so users
  can :ref:`print a completion script <print-completion-script>` which
  automatically matches the emitting binary's configured names (compared to the
  previous hardcoded scripts, which only worked for ``inv``/``invoke`` by
  default). Thanks to Nicolas Höning for the foundational patchset.
- :release:`1.1.1 <2018-07-31>`
- :release:`1.0.2 <2018-07-31>`
- :bug:`556` (also `fabric/fabric#1823
  <https://github.com/fabric/fabric/issues/1823>`_) Pre-emptively check for an
  error condition involving an unpicklable config file value (Python config
  files and imported module objects) and raise a useful exception instead of
  allowing a confusing ``TypeError`` to bubble up later. Reported by Pham Cong
  Dinh.
- :bug:`559` (also `fabric/fabric#1812
  <https://github.com/fabric/fabric/issues/1812>`_) Modify how
  `~invoke.runners.Runner` performs stdin terminal mode changes, to avoid
  incorrect terminal state restoration when run concurrently (which could lead
  to things like terminal echo becoming disabled after the Python process
  exits).

  Thanks to Adam Jensen and Nick Timkovich for the detailed bug reports &
  reproduction assistance.
- :release:`1.1.0 <2018-07-12>`
- :release:`1.0.1 <2018-07-12>`
- :feature:`-` Enhance `~invoke.tasks.Call` with a new method
  (``clone_data``) and new kwarg to an existing method (``clone`` grew
  ``with_``) to assist subclassers when extending.
- :bug:`270` (also :issue:`551`) ``None`` values in config levels (most
  commonly caused by empty configuration files) would raise ``AttributeError``
  when `~invoke.config.merge_dicts` was used to merge config levels together.
  This has been fixed. Thanks to Tyler Hoffman and Vlad Frolov for the reports.
- :feature:`-` Refactor `~invoke.tasks.Call` internals slightly, exposing some
  previously internal logic as the ``clone_data`` method; this is useful for
  client codebases when extending `~invoke.tasks.Call` and friends.
- :feature:`-` Remove overzealous argument checking in `@task
  <invoke.tasks.task>`, instead just handing any extra kwargs into the task
  class constructor. The high level behavior for truly invalid kwargs is the
  same (``TypeError``) but now extending codebases can add kwargs to their
  versions of ``@task`` without issue.
- :feature:`-` Add a ``klass`` kwarg to `@task <invoke.tasks.task>` to allow
  extending codebases the ability to create their own variants on
  ``@task``/``Task``.
- :bug:`-` Fix up the ``__repr__`` of `~invoke.tasks.Call` to reference dynamic
  class name instead of hardcoding ``"Call"``; this allows subclasses'
  ``__repr__`` output to be correct instead of confusing.
- :support:`- backported` Fixed some inaccuracies in the API docs around
  `~invoke.executor.Executor` and its ``core`` kwarg (was erroneously referring
  to `~invoke.parser.context.ParserContext` instead of
  `~invoke.parser.parser.ParseResult`). Includes related cleaning-up of
  docstrings and tests.
- :support:`- backported` Apply the `black <https://black.readthedocs.io/>`_
  code formatter to our codebase and our CI configuration.
- :support:`- backported` Fix some test-suite-only failures preventing
  successful testing on Python 3.7 and PyPy3, and move them out of the 'allowed
  failures' test matrix quarantine now that they pass.
- :support:`- backported` Implemented some minor missing tests, such as testing
  the ``INVOKE_DEBUG`` low-level env var.
- :feature:`543` Implemented support for using ``INVOKE_RUNTIME_CONFIG`` env
  var as an alternate method of supplying a runtime configuration file path
  (effectively, an env var based version of using the ``-f``/``--config``
  option). Feature request via Kevin J. Qiu.
- :bug:`528` Around Invoke 0.23 we broke the ability to weave in subcollections
  via keyword arguments to `~invoke.collection.Collection`, though it primarily
  manifests as ``NoneType`` related errors during ``inv --list``. This was
  unintentional and has been fixed. Report submitted by Tuukka Mustonen.
- :bug:`-` As part of solving :issue:`528` we found a related bug, where
  unnamed subcollections also caused issues with ``inv --list
  --list-format=json``. Specifically, `Collection.serialized
  <invoke.collection.Collection.serialized>` sorts subcollections by name,
  which is problematic when that name is ``None``. This is now fixed.
- :release:`1.0.0 <2018-05-09>`
- :feature:`-` Added the :ref:`--prompt-for-sudo-password
  <prompt-for-sudo-password>` CLI option for getpass-based up-front prompting
  of a sensitive configuration value.
- :feature:`-` Updated `~invoke.tasks.Task` to mimic the wrapped function's
  ``__module__`` attribute, allowing for better interaction with things like
  Sphinx autodoc that attempt to filter out imported objects from a module.
- :bug:`- major` Removed an old, unused and untested (but, regrettably,
  documented and public) method that doesn't seem to be much use:
  ``invoke.config.Config.paths``. Please reach out if you were actually using
  it and we may consider adding some form of it back.

  .. warning::
    This is a backwards incompatible change if you were using ``Config.paths``.

- :bug:`- major` Tweaked the innards of
  `~invoke.config.Config`/`~invoke.config.DataProxy` to prevent accessing
  properties & other attributes' values during ``__setattr__`` (the code in
  question only needed the names). This should have no noticeable effect on
  user code (besides a marginal speed increase) but fixed some minor test
  coverage issues.
- :release:`0.23.0 <2018-04-29>`
- :bug:`- major` Previously, some error conditions (such as invalid task or
  collection names being supplied by the user) printed to standard output,
  instead of standard error. Standard error seems more appropriate here, so
  this has been fixed.

  .. warning::
    This is backwards incompatible if you were explicitly checking the standard
    output of the ``inv[oke]`` program for some of these error messages.

  .. warning::
    If your code is manually raising or introspecting instances of
    `~invoke.exceptions.Exit`, note that its signature has changed from
    ``Exit(code=0)`` to ``Exit(message=None, code=None)``. (Thus, this will
    only impact you if you were calling its constructor instead of raising the
    class object itself.)

- :bug:`- major` `~invoke.collection.Collection` had some minor bugs or
  oversights in how it responds to things like ``repr()``, ``==``; boolean
  behavior; how docstrings appear when created from a Python module; etc. All
  are now fixed. If you're not sure whether this affects you, it does not :)
- :bug:`- major` Integer-type CLI arguments were not displaying placeholder
  text in ``--help`` output (i.e. they appeared as ``--myint`` instead of
  ``--myint=INT``.) This has been fixed.
- :feature:`33` Overhaul task listing (formerly just a simple, boolean
  ``--list``) to make life easier for users with nontrivial task trees:

  - Limit display to a specific namespace by giving an optional argument to
    ``--list``, e.g. ``--list build``;
  - Additional output formats besides the default (now known as ``flat``) such
    as a nested view with ``--list-format nested`` or script-friendly output
    with ``--list-format json``.
  - The default ``flat`` format now sorts a bit differently - the previous
    algorithm would break up trees of tasks.
  - Limit listing depth, so it's easier to view only the first level or two
    (i.e. the overall namespaces) of a large tree, e.g. ``--list --list-depth
    1``;

  Thanks to the many users who submitted various requests under this ticket's
  umbrella, and to Dave Burkholder in particular for detailed use case analysis
  & feedback.

- :support:`-` (partially re: :issue:`33`) Renamed the ``--root`` CLI flag to
  ``--search-root``, partly for clarity (:issue:`33` will be adding namespace
  display-root related flags, which would make ``--root`` ambiguous) and partly
  for consistency with the config option, which was already named
  ``search_root``. (The short version of the flag, ``-r``, is unchanged.)

  .. warning::
    This is a backwards incompatible change. To fix, simply use
    ``--search-root`` anywhere you were previously using ``--root``.
- :bug:`516 major` Remove the CLI parser ambiguity rule regarding flag-like
  tokens which are seen after an optional-value flag (e.g. ``inv task
  --optionally-takes-a-value --some-other-flag``.) Previously, any flag-like
  value in such a spot was considered ambiguous and raised a
  `~invoke.exceptions.ParseError`. Now, the surrounding parse context is used
  to resolve the ambiguity, and no error is raised.

  .. warning::
    This behavior is backwards incompatible, but only if you had the minority
    case where users frequently *and erroneously* give otherwise-legitimate
    flag-like values to optional-value arguments, and you rely on the parse
    errors to notify them of their mistake. (If you don't understand what this
    means, don't worry, you almost certainly don't need to care!)

- :support:`515` Ported the test suite from `spec
  <https://github.com/bitprophet/spec>`_ (`nose
  <https://nose.readthedocs.io>`_) to `pytest-relaxed
  <https://github.com/bitprophet/pytest-relaxed>`_ (`pytest
  <https://pytest.org>`_) as pytest basically won the test-runner war against
  nose & has greater mindshare, more shiny toys, etc.
- :support:`-` Rename ``invoke.platform`` to ``invoke.terminals``; it was
  inadvertently shadowing the ``platform`` standard library builtin module.
  This was not causing any bugs we are aware of, but it is still poor hygiene.

  .. warning::
    This change is technically backwards incompatible. We don't expect many
    users import ``invoke.platform`` directly, but if you are, take note.

- :bug:`- major` (partially re: :issue:`449`) Update error message around
  missing positional arguments so it actually lists them. Includes a minor
  tweak to the API of `~invoke.parser.context.ParserContext`, namely changing
  ``needs_positional_arguments`` (bool) to ``missing_positional_arguments``
  (list).
- :release:`0.22.1 <2018-01-29>`
- :bug:`342` Accidentally hardcoded ``Collection`` instead of ``cls`` in
  `Collection.from_module <invoke.collection.Collection.from_module>` (an
  alternate constructor and therefore a classmethod.) This made it rather hard
  to properly subclass `~invoke.collection.Collection`. Report and initial
  patch courtesy of Luc Saffre.
- :support:`433 backported` Add -dev and -nightly style Python versions to our
  Travis builds. Thanks to ``@SylvainDe`` for the contribution.
- :bug:`437` When merging configuration levels together (which uses
  `copy.copy` by default), pass file objects by reference so they don't get
  closed. Catch & patch by Paul Healy.
- :support:`469 backported` Fix up the :ref:`doc/example
  <customizing-config-defaults>` re: subclassing `~invoke.config.Config`.
  Credit: ``@Aiky30``.
- :bug:`488` Account for additional I/O related ``OSError`` error strings
  when attempting to capture only this specific subtype of error. This should
  fix some issues with less common libc implementations such as ``musl`` (as
  found on e.g. Alpine Linux.) Thanks to Rajitha Perera for the report.
- :release:`0.22.0 <2017-11-29>`
- :bug:`407 major` (also :issue:`494`, :issue:`67`) Update the default value of
  the ``run.shell`` config value so that it reflects a Windows-appropriate
  value (specifically, the ``COMSPEC`` env var or a fallback of ``cmd.exe``) on
  Windows platforms. This prevents Windows users from being forced to always
  ship around configuration-level overrides.

  Thanks to Maciej 'maQ' Kusz for the original patchset, and to ``@thebjorn``
  and Garrett Jenkins for providing lots of feedback.
- :bug:`- major` Iterable-type CLI args were actually still somewhat broken &
  were 'eating' values after themselves in the parser stream (thus e.g.
  preventing parsing of subsequent tasks or flags.) This has been fixed.
- :support:`364` Drop Python 2.6 and Python 3.3 support, as these versions now
  account for only very low percentages of the userbase and are unsupported (or
  about to be unsupported) by the rest of the ecosystem, including ``pip``.

  This includes updating documentation & packaging metadata as well as taking
  advantage of basic syntax additions like set literals/comprehensions (``{1,
  2, 3}`` instead of ``set([1, 2, 3])``) and removing positional string
  argument specifiers (``"{}".format(val)`` instead of ``"{0}".format(val)``).

- :release:`0.21.0 <2017-09-18>`
- :feature:`132` Implement 'iterable' and 'incrementable' CLI flags, allowing
  for invocations like ``inv mytask --listy foo --listy bar`` (resulting in a
  call like ``mytask(listy=['foo', 'bar'])``) or ``inv mytask -vvv`` (resulting
  in e.g. ``mytask(verbose=3)``. Specifically, these require use of the new
  :ref:`iterable <iterable-flag-values>` and :ref:`incrementable
  <incrementable-flag-values>` arguments to `@task <invoke.tasks.task>` - see
  those links to the conceptual docs for details.
- :release:`0.20.4 <2017-08-14>`
- :bug:`-` The behavior of `Config <invoke.config.Config>` when ``lazy=True``
  didn't match that described in the API docs, after the recent updates to its
  lifecycle. (Specifically, any config data given to the constructor was not
  visible in the resulting instance until ``merge()`` was explicitly called.)
  This has been fixed, along with other related minor issues.
- :release:`0.20.3 <2017-08-04>`
- :bug:`467` (Arguably also a feature, but since it enables behavior users
  clearly found intuitive, we're considering it a bug.) Split up the parsing
  machinery of `Program <invoke.program.Program>` and pushed the `Collection
  <invoke.collection.Collection>`-making out of `Loader
  <invoke.loader.Loader>`. Combined, this allows us to honor the project-level
  config file *before* the second (task-oriented) CLI parsing step, instead of
  after.

  For example, this means you can turn off ``auto_dash_names`` in your
  per-project configs and not only in your system or user configs.

  Report again courtesy of Luke Orland.

  .. warning::
    This is a backwards incompatible change *if* you were subclassing and
    overriding any of the affected methods in the ``Program`` or ``Loader``
    classes.

- :release:`0.20.2 <2017-08-02>`
- :bug:`465` The ``tasks.auto_dash_names`` config option added in ``0.20.0``
  wasn't being fully honored when set to ``False``; this has been fixed. Thanks
  to Luke Orland for the report.
- :release:`0.20.1 <2017-07-27>`
- :bug:`-` Fix a broken ``six.moves`` import within ``invoke.util``; was
  causing ``ImportError`` in environments without an external copy of ``six``
  installed.

  The dangers of one's local and CI environments all pulling down packages that
  use ``six``! It's everywhere!
- :release:`0.20.0 <2017-07-27>`
- :feature:`-` (required to support :issue:`310` and :issue:`329`) Break up the
  `~invoke.config.Config` lifecycle some more, allowing it to gradually load
  configuration vectors; this allows the CLI machinery
  (`~invoke.executor.Executor`) to honor configuration settings from config
  files which impact how CLI parsing and task loading behaves.

  Specifically, this adds more public ``Config.load_*`` methods, which in
  tandem with the ``lazy`` kwarg to ``__init__`` (formerly ``defer_post_init``,
  see below) allow full control over exactly when each config level is loaded.

  .. warning::
    This change may be backwards incompatible if you were using or subclassing
    the `~invoke.config.Config` class in any of the following ways:

    - If you were passing ``__init__`` kwargs such as ``project_home`` or
      ``runtime_path`` and expecting those files to auto-load, they no longer
      do; you must explicitly call `~invoke.config.Config.load_project` and/or
      `~invoke.config.Config.load_runtime` explicitly.
    - The ``defer_post_init`` keyword argument to ``Config.__init__`` has been
      renamed to ``lazy``, and controls whether system/user config files are
      auto-loaded.
    - ``Config.post_init`` has been removed, in favor of explicit/granular use
      of the ``load_*`` family of methods.
    - All ``load_*`` methods now call ``Config.merge`` automatically by default
      (previously, merging was deferred to the end of most config related
      workflows.)

      This should only be a problem if your config contents are extremely large
      (it's an entirely in-memory dict-traversal operation) and can be avoided
      by specifying ``merge=False`` to any such method. (Note that you must, at
      some point, call `~invoke.config.Config.merge` in order for the config
      object to work normally!)

- :feature:`310` (also :issue:`455`, :issue:`291`) Allow configuring collection
  root directory & module name via configuration files (previously, they were
  only configurable via CLI flags or generating a custom
  `~invoke.program.Program`.)
- :feature:`329` All task and collection names now have underscores turned into
  dashes automatically, as task parameters have been for some time. This
  impacts ``--list``, ``--help``, and of course the parser. For details, see
  :ref:`dashes-vs-underscores`.

  This behavior is controlled by a new config setting,
  ``tasks.auto_dash_names``, which can be set to ``False`` to go back to the
  classic behavior.

  Thanks to Alexander Artemenko for the initial feature request.
- :bug:`396 major` ``Collection.add_task(task, aliases=('other', 'names')`` was
  listed in the conceptual documentation, but not implemented (technically, it
  was removed at some point and never reinstated.) It has been (re-)added and
  now exists. Thanks to ``@jenisys`` for the report.

  .. warning::
    This technically changes argument order for `Collection.add_task
    <invoke.collection.Collection.add_task>`, so be aware if you were using
    positional arguments!

- :bug:`- major` Display of hidden subprocess output when a command
  execution failed (end-of-session output starting with ``Encountered a bad
  command exit code!``) was liable to display encoding errors (e.g. ``'ascii'
  codec can't encode character ...``) when that output was not
  ASCII-compatible.

  This problem was previously solved for *non-hidden* (mirrored) subprocess
  output, but the fix (encode the data with the local encoding) had not been
  applied to exception display. Now it's applied in both cases.
- :feature:`322` Allow users to completely disable mirroring of stdin to
  subprocesses, by specifying ``False`` for the ``run.in_stream`` config
  setting and/or keyword argument.

  This can help prevent problems when running Invoke under systems that have no
  useful standard input and which otherwise defeat our pty/fileno related
  detection.
- :release:`0.19.0 <2017-06-19>`
- :feature:`-` Add `MockContext.set_result_for
  <invoke.context.MockContext.set_result_for>` to allow massaging a mock
  Context's configured results after instantiation.
- :release:`0.18.1 <2017-06-07>`
- :bug:`-` Update Context internals re: command execution & configuration of
  runner subclasses, to work better in client libraries such as Fabric 2.

    .. note::
        If you were using the undocumented ``runner`` configuration value added
        in :issue:`446`, it is now ``runners.local``.

    .. warning::
        This change modifies the internals of methods like
        `~invoke.context.Context.run` and `~invoke.context.Context.sudo`; users
        maintaining their own subclasses should be aware of possible breakage.

- :release:`0.18.0 <2017-06-02>`
- :feature:`446` Implement `~invoke.context.Context.cd` and
  `~invoke.context.Context.prefix` context managers (as methods on the
  not-that-one-the-other-one `~invoke.context.Context` class.) These are based
  on similar functionality in Fabric 1.x. Credit: Ryan P Kilby.
- :support:`448` Fix up some config-related tests that have been failing on
  Windows for some time. Thanks to Ryan P Kilby.
- :feature:`205` Allow giving core flags like ``--help`` after tasks to trigger
  per-task help. Previously, only ``inv --help taskname`` worked.

  .. note::
      Tasks with their own ``--help`` flags won't be able to leverage this
      feature - the parser will still interpret the flag as being per-task and
      not global. This may change in the future to simply throw an exception
      complaining about the ambiguity. (Feedback welcome.)

- :feature:`444` Add support for being used as ``python -m invoke <args>`` on
  Python 2.7 and up. Thanks to Pekka Klärck for the feature request.
- :release:`0.17.0 <2017-05-05>`
- :bug:`439 major` Avoid placing stdin into bytewise read mode when it looks
  like Invoke has been placed in the background by a shell's job control
  system; doing so was causing the shell to pause the Invoke process (e.g. with
  a message like ``suspended (tty output)``.) Reported by Tuukka Mustonen.
- :bug:`425 major` Fix ``Inappropriate ioctl for device`` errors (usually
  ``OSError``) when running Invoke without a tty-attached stdin (i.e. when run
  under 'headless' continuous integration systems or simply as e.g. ``inv
  sometask < /dev/null`` (redirected stdin.) Thanks to Javier Domingo Cansino
  for the report & Tuukka Mustonen for troubleshooting assistance.
- :feature:`-` Add a ``user`` kwarg & config parameter to
  `Context.sudo <invoke.context.Context.sudo>`, which corresponds roughly to
  ``sudo -u <user> <command>``.
- :bug:`440 major` Make sure to skip a call to ``struct``/``ioctl`` on Windows
  platforms; otherwise certain situations inside ``run`` calls would trigger
  import errors. Thanks to ``@chrisc11`` for the report.
- :release:`0.16.3 <2017-04-18>`
- :bug:`-` Even more setup.py related tomfoolery.
- :release:`0.16.2 <2017-04-18>`
- :bug:`-` Deal with the fact that PyPI's rendering of Restructured Text has no
  idea about our fancy new use of Sphinx's doctest module. Sob.
- :release:`0.16.1 <2017-04-18>`
- :bug:`-` Fix a silly typo preventing proper rendering of the packaging
  ``long_description`` (causing an effectively blank PyPI description.)
- :release:`0.16.0 <2017-04-18>`
- :feature:`232` Add support for ``.yml``-suffixed config files (in addition to
  ``.yaml``, ``.json`` and ``.py``.) Thanks to Matthias Lehmann for the
  original request & Greg Back for an early patch.
- :feature:`418` Enhance ability of client libraries to override config
  filename prefixes. This includes modifications to related functionality, such
  as how env var prefixes are configured.

  .. warning::
    **This is a backwards incompatible change** if:

    - you were relying on the ``env_prefix`` keyword argument to
      `Config.__init__ <invoke.config.Config.__init__>`; it is now the
      ``prefix`` or ``env_prefix`` class attribute, depending.
    - or the kwarg/attribute of the same name in `Program.__init__
      <invoke.program.Program.__init__>`; you should now be subclassing
      ``Config`` and using its ``env_prefix`` attribute;
    - or if you were relying on how standalone ``Config`` objects defaulted to
      having a ``None`` value for ``env_prefix``, and thus loaded env vars
      without an ``INVOKE_`` style prefix.

      See new documentation for this functionality at
      :ref:`customizing-config-defaults` for details.

- :feature:`309` Overhaul how task execution contexts/configs are handled, such
  that all contexts in a session now share the same config object, and thus
  user modifications are preserved between tasks. This has been done in a
  manner that should not break things like collection-based config (which may
  still differ from task to task.)

  .. warning::
    **This is a backwards incompatible change** if you were relying on the
    post-0.12 behavior of cloning config objects between each task execution.
    Make sure to investigate if you find tasks affecting one another in
    unexpected ways!

- :support:`-` Fixed some Python 2.6 incompatible string formatting that snuck
  in recently.
- :feature:`-` Switched the order of the first two arguments of
  `Config.__init__ <invoke.config.Config.__init__>`, so that the ``overrides``
  kwarg becomes the first positional argument.

  This supports the common use case of making a `Config <invoke.config.Config>`
  object that honors the system's core/global defaults; previously, because
  ``defaults`` was the first argument, you'd end up replacing those core
  defaults instead of merging with them.

  .. warning::
    **This is a backwards incompatible change** if you were creating custom
    ``Config`` objects via positional, instead of keyword, arguments. It should
    have no effect otherwise.

- :feature:`-` `Context.sudo <invoke.context.Context.sudo>` no longer prompts
  the user when the configured sudo password is empty; thus, an empty sudo
  password and a ``sudo`` program configured to require one will result in an
  exception.

  The runtime prompting for a missing password was a temporary holdover from
  Fabric v1, and in retrospect is undesirable. We may add it back in as an
  opt-in behavior (probably via subclassing) in the future if anybody misses
  it.

  .. warning::
    **This is a backwards incompatible change**, if you were relying on
    ``sudo()`` prompting you for your password (vs configuring it). If you
    *were* doing that, you can simply switch to ``run("sudo <command>")`` and
    respond to the subprocess' sudo prompt by hand instead.

- :feature:`-` `Result <invoke.runners.Result>` and `UnexpectedExit
  <invoke.exceptions.UnexpectedExit>` objects now have a more useful ``repr()``
  (and in the case of ``UnexpectedExit``, a distinct ``repr()`` from their
  preexisting ``str()``.)
- :bug:`432 major` Tighten application of IO thread ``join`` timeouts (in `run
  <invoke.runners.Runner.run>`) to only happen when :issue:`351` appears
  actually present. Otherwise, slow/overworked IO threads had a chance of being
  joined before truly reading all data from the subprocess' pipe.
- :bug:`430 major` Fallback importing of PyYAML when Invoke has been installed
  without its vendor directory, was still trying to import the vendorized
  module names (e.g. ``yaml2`` or ``yaml3`` instead of simply ``yaml``). This
  has been fixed, thanks to Athmane Madjoudj.
- :release:`0.15.0 <2017-02-14>`
- :bug:`426 major` `DataProxy <invoke.config.DataProxy>` based classes like
  `Config <invoke.config.Config>` and `Context <invoke.context.Context>` didn't
  like being `pickled <pickle>` or `copied <copy.copy>` and threw
  ``RecursionError``. This has been fixed.
- :feature:`-` `Config <invoke.config.Config>`'s internals got cleaned up
  somewhat; end users should not see much of a difference, but advanced
  users or authors of extension code may notice the following:

  - Direct modification of config data (e.g. ``myconfig.section.subsection.key
    = 'value'`` in user/task code) is now stored in its own config 'level'/data
    structure; previously such modifications simply mutated the central,
    'merged' config cache. This makes it much easier to determine where a final
    observed value came from, and prevents accidental data loss.
  - Ditto for deleted values.
  - Merging/reconciliation of the config levels now happens automatically when
    data is loaded or modified, which not only simplifies the object's
    lifecycle a bit but allows the previous change to function without
    requiring users to call ``.merge()`` after every modification.

- :bug:`- major` Python 3's hashing rules differ from Python 2, specifically:

    A class that overrides ``__eq__()`` and does not define ``__hash__()`` will
    have its ``__hash__()`` implicitly set to None.

  `Config <invoke.config.Config>` (specifically, its foundational class
  `DataProxy <invoke.config.DataProxy>`) only defined ``__eq__`` which,
  combined with the above behavior, meant that ``Config`` objects appeared to
  hash successfully on Python 2 but yielded ``TypeErrors`` on Python 3.

  This has been fixed by explicitly setting ``__hash__ = None`` so that the
  objects do not hash on either interpreter (there are no good immutable
  attributes by which to define hashability).
- :bug:`- major` Configuration keys named ``config`` were inadvertently
  exposing the internal dict representation of the containing config object,
  instead of displaying the actual value stored in that key. (Thus, a set
  config of ``mycontext.foo.bar.config`` would act as if it was the key/value
  contents of the ``mycontext.foo.bar`` subtree.) This has been fixed.
- :feature:`421` Updated `Config.clone <invoke.config.Config.clone>` (and a few
  other related areas) to replace use of `copy.deepcopy` with a less-rigorous
  but also less-likely-to-explode recursive dict copier. This prevents
  frustrating ``TypeErrors`` while still preserving barriers between different
  tasks' configuration values.
- :feature:`-` `Config.clone <invoke.config.Config.clone>` grew a new ``into``
  kwarg allowing client libraries with their own `~invoke.config.Config`
  subclasses to easily "upgrade" vanilla Invoke config objects into their local
  variety.
- :bug:`419 major` Optional parser arguments had a few issues:

  - The :ref:`conceptual docs about CLI parsing <optional-values>` mentioned
    them, but didn't actually show via example how to enable the feature,
    implying (incorrectly) that they were active always by default. An example
    has been added.
  - Even when enabled, they did not function correctly when their default
    values were of type ``bool``; in this situation, trying to give a value (vs
    just giving the flag name by itself) caused a parser error.  This has been
    fixed.

  Thanks to ``@ouroboroscoding`` for the report.
- :support:`204` (via :issue:`412`) Fall back to globally-installed copies of
  our vendored dependencies, if the import from the ``vendor`` tree fails. In
  normal situations this won't happen, but it allows advanced users or
  downstream maintainers to nuke ``vendor/`` and prefer explicitly installed
  packages of e.g. ``six``, ``pyyaml`` or ``fluidity``. Thanks to Athmane
  Madjoudj for the patch.
- :bug:`- major` Fix configuration framework such that nested or dict-like
  config values may be compared with regular dicts. Previously, doing so caused
  an ``AttributeError`` (as regular dicts lack a ``.config``).
- :bug:`413 major` Update behavior of ``DataProxy`` (used within
  `~invoke.context.Context` and `~invoke.config.Config`) again, fixing two
  related issues:

  - Creating new configuration keys via attribute access wasn't possible: one
    had to do ``config['foo'] = 'bar'`` because ``config.foo = 'bar'`` would
    set a real attribute instead of touching configuration.
  - Supertypes' attributes weren't being considered during the "is this a real
    attribute on ``self``?" test, leading to different behavior between a
    nested config-value-as-attribute and a top-level Context/Config one.

- :release:`0.14.0 <2016-12-05>`
- :bug:`349 major` Display the string representation of
  `~invoke.exceptions.UnexpectedExit` when handling it inside of
  `~invoke.program.Program` (including regular ``inv``), if any output was
  hidden during the ``run`` that generated it.

  Previously, we only exited with the exception's stored exit code, meaning
  failures of ``run(..., hide=True)`` commands were unexpectedly silent.
  (Library-style use of the codebase didn't have this problem, since tracebacks
  aren't muted.)

  While implementing this change, we also tweaked the overall display of
  ``UnexpectedExit`` so it's a bit more consistent & useful:

  - noting "hey, you ran with ``pty=True``, so there's no stderr";
  - showing only the last 10 lines of captured output in the error message
    (users can, of course, always manually handle the error & access the full
    thing if desired);
  - only showing a given stream when it was not already printed to the user's
    terminal (i.e. if ``hide=False``, no captured output is shown in the error
    text; if ``hide='stdout'``, only stdout is shown in the error text; etc.)

  Thanks to Patrick Massot for the original bug report.

- :feature:`-` Expose the (normalized) value of `~invoke.runners.Runner.run`'s
  ``hide`` parameter in its return-value `~invoke.runners.Result` objects.
- :bug:`288 major` Address a bug preventing reuse of Invoke as a custom
  binstub, by moving ``--list`` into the "core args" set of flags present on
  all Invoke-derived binstubs. Thanks to Jordon Mears for catch & patch.
- :bug:`283 major` Fix the concepts/library docs so the example of an explicit
  ``namespace=`` argument correctly shows wrapping an imported task module in a
  `~invoke.collection.Collection`. Thanks to ``@zaiste`` for the report.
- :bug:`- major` Fix ``DataProxy`` (used within `~invoke.context.Context` and
  `~invoke.config.Config`) so that real attributes and methods which are
  shadowed by configuration keys, aren't proxied to the config during regular
  attribute get/set. (Such config keys are thus required to be accessed via
  dict-style only, or (on `~invoke.context.Context`) via the explicit
  ``.config`` attribute.)
- :bug:`58 major` Work around bugs in ``select()`` when handling subprocess
  stream reads, which was causing poor behavior in many nontrivial interactive
  programs (such as ``vim`` and other fullscreen editors, ``python`` and other
  REPLs/shells, etc). Such programs should now be largely indistinguishable
  from their behavior when run directly from a user's shell.
- :feature:`406` Update handling of Ctrl-C/``KeyboardInterrupt``, and
  subprocess exit status pass-through, to be more correct than before:

  - Submit the interrupt byte sequence ``\x03`` to stdin of all subprocesses,
    instead of sending ``SIGINT``.

      - This results in behavior closer to that of truly pressing Ctrl-C when
        running subprocesses directly; for example, interactive programs like
        ``vim`` or ``python`` now behave normally instead of prematurely
        exiting.
      - Of course, programs that would normally exit on Ctrl-C will still do
        so!

  - The exit statuses of subprocesses run with ``pty=True`` are more rigorously
    checked (using `os.WIFEXITED` and friends), allowing us to surface the real
    exit values of interrupted programs instead of manually assuming exit code
    ``130``.

      - Typically, this will be exit code ``-2``, but it is system dependent.
      - Other, non-Ctrl-C-driven signal-related exits under PTYs should behave
        better now as well - previously they could appear to exit ``0``!

  - Non-subprocess-related ``KeyboardInterrupt`` (i.e. those generated when
    running top level Python code outside of any ``run`` function calls)
    will now trigger exit code ``1``, as that is how the Python interpreter
    typically behaves if you ``KeyboardInterrupt`` it outside of a live
    REPL.

  .. warning::
    These changes are **backwards incompatible** if you were relying on the
    "exits ``130``" behavior added in version 0.13, or on the (incorrect)
    ``SIGINT`` method of killing pty-driven subprocesses on Ctrl-C.

- :bug:`- major` Correctly raise ``TypeError`` when unexpected keyword
  arguments are given to `~invoke.runners.Runner.run`.
- :feature:`-` Add a `~invoke.context.MockContext` class for easier testing of
  user-written tasks and related client code. Includes adding a
  :ref:`conceptual document on how to test Invoke-using code
  <testing-user-code>`.
- :feature:`-` Update implementation of `~invoke.runners.Result` so it has
  default values for all parameters/attributes. This allows it to be more
  easily used when mocking ``run`` calls in client libraries' tests.

  .. warning::
    This is a backwards incompatible change if you are manually instantiating
    `~invoke.runners.Result` objects with positional arguments: positional
    argument order has changed. (Compare the API docs between versions to see
    exactly how.)

- :feature:`294` Implement `Context.sudo <invoke.context.Context.sudo>`, which
  wraps `~invoke.context.Context.run` inside a ``sudo`` command. It is capable
  of auto-responding to ``sudo``'s password prompt with a configured password,
  and raises a specific exception (`~invoke.exceptions.AuthFailure`) if that
  password is rejected.
- :feature:`369` Overhaul the autoresponse functionality for `~invoke.run` so
  it's significantly more extensible, both for its own sake and as part of
  implementing :issue:`294` (see its own changelog entry for details).

  .. warning::
      This is a backwards incompatible change: the ``responses`` kwarg to
      ``run()`` is now ``watchers``, and accepts a list of
      `~invoke.watchers.StreamWatcher` objects (such as
      `~invoke.watchers.Responder`) instead of a dict.

      If you were using ``run(..., responses={'pattern': 'response'}``
      previously, just update to instead use ``run(...,
      watchers=[Responder('pattern', 'response')])``.

- :bug:`- major` Fix a bug in `Config.clone <invoke.config.Config.clone>` where
  it was instantiating a new ``Config`` instead of a member of the subclass.
- :release:`0.13.0 <2016-06-09>`
- :feature:`114` Ripped off the band-aid and removed non-contextualized tasks
  as an option; all tasks must now be contextualized (defined as ``def
  mytask(context, ...)`` - see :ref:`defining-and-running-task-functions`) even
  if not using the context. This simplifies the implementation as well as
  users' conceptual models. Thanks to Bay Grabowski for the patch.

  .. warning:: This is a backwards incompatible change!

- :bug:`350 major` (also :issue:`274`, :issue:`241`, :issue:`262`,
  :issue:`242`, :issue:`321`, :issue:`338`) Clean up and reorganize
  encoding-related parts of the code to avoid some of the more common or
  egregious encode/decode errors surrounding clearly non-ASCII-compatible text.
  Bug reports, assistance, feedback and code examples courtesy of Paul Moore,
  Vlad Frolov, Christian Aichinger, Fotis Gimian, Daniel Nunes, and others.
- :bug:`351 major` Protect against ``run`` deadlocks involving exceptions in
  I/O threads & nontrivial amounts of unread data in the corresponding
  subprocess pipe(s). This situation should now always result in exceptions
  instead of hangs.
- :feature:`259` (also :issue:`280`) Allow updating (or replacing) subprocess
  shell environments, via the ``env`` and ``replace_env`` kwargs to
  `~invoke.runners.Runner.run`. Thanks to Fotis Gimian for the report,
  ``@philtay`` for an early version of the final patch, and Erich Heine & Vlad
  Frolov for feedback.
- :feature:`67` Added ``shell`` option to `~invoke.runners.Runner.run`,
  allowing control of the shell used when invoking commands. Previously,
  ``pty=True`` used ``/bin/bash`` and ``pty=False`` (the default) used
  ``/bin/sh``; the new unified default value is ``/bin/bash``.

  Thanks to Jochen Breuer for the report.
- :bug:`152 major` (also :issue:`251`, :issue:`331`) Correctly handle
  ``KeyboardInterrupt`` during `~invoke.runners.Runner.run`, re: both mirroring
  the interrupt signal to the subprocess *and* capturing the local exception
  within Invoke's CLI handler (so there's no messy traceback, just exiting with
  code ``130``).

  Thanks to Peter Darrow for the report, and to Mika Eloranta & Máté Farkas for
  early versions of the patchset.
- :support:`319` Fixed an issue resulting from :issue:`255` which
  caused problems with how we generate release wheels (notably, some releases
  such as 0.12.1 fail when installing from wheels on Python 2).

  .. note::
    As part of this fix, the next release will distribute individual Python 2
    and Python 3 wheels instead of one 'universal' wheel. This change should be
    transparent to users.

  Thanks to ``@ojos`` for the initial report and Frazer McLean for some
  particularly useful feedback.
- :release:`0.12.2 <2016-02-07>`
- :support:`314 backported` (Partial fix.) Update ``MANIFEST.in`` so source
  distributions include some missing project-management files (e.g. our
  internal ``tasks.py``). This makes unpacked sdists more useful for things
  like running the doc or build tasks.
- :bug:`303` Make sure `~invoke.run` waits for its IO worker threads to cleanly
  exit (such as allowing a ``finally`` block to revert TTY settings) when
  ``KeyboardInterrupt`` (or similar) aborts execution in the main thread.
  Thanks to Tony S Yu and Máté Farkas for the report.
- :release:`0.12.1 <2016-02-03>`
- :bug:`308` Earlier changes to TTY detection & its use in determining features
  such as stdin pass-through, were insufficient to handle edge cases such as
  nested Invoke sessions or piped stdin to Invoke processes. This manifested as
  hangs and ``OSError`` messages about broken pipes.

  The issue has been fixed by overhauling all related code to use more specific
  and accurate checks (e.g. examining just ``fileno`` and/or just ``isatty``).

  Thanks to Tuukka Mustonen and Máté Farkas for the report (and for enduring
  the subsequent flood of the project maintainer's stream-of-consciousness
  ticket updates).
- :bug:`305` (also :issue:`306`) Fix up some test-suite issues causing failures
  on Windows/Appveyor. Thanks to Paul Moore.
- :bug:`289` Handful of issues, all fallout from :issue:`289`, which failed to
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

- :release:`0.12.0 <2016-01-12>`
- :bug:`257 major` Fix a RecursionError under Python 3 due to lack of
  ``__deepcopy__`` on `~invoke.tasks.Call` objects. Thanks to Markus
  Zapke-Gründemann for initial report and Máté Farkas for the patch.
- :support:`265` Update our Travis config to select its newer build
  infrastructure and also run on PyPy3. Thanks to Omer Katz.
- :support:`254` Add an ``exclude`` option in our ``setup.py`` so setuptools
  doesn't try loading our vendored PyYAML's Python 2 sub-package under Python 3
  (or vice versa - though all reports were from Python 3 users). Thanks to
  ``@yoshiya0503`` for catch & initial patch.
- :feature:`68` Disable Python's bytecode caching by default, as it complicates
  our typical use case (frequently-changing .py files) and offers little
  benefit for human-facing startup times. Bytecode caching can be explicitly
  re-enabled by specifying ``--write-pyc`` at runtime. Thanks to Jochen Breuer
  for feature request and ``@brutus`` for initial patchset.
- :support:`144` Add code-coverage reporting to our CI builds (albeit `CodeCov
  <https://codecov.io>`_ instead of `coveralls.io <https://coveralls.io>`_).
  Includes rejiggering our project-specific coverage-generating tasks. Thanks
  to David Baumgold for the original request/PR and to Justin Abrahms for the
  tipoff re: CodeCov.
- :bug:`297 major` Ignore leading and trailing underscores when turning task
  arguments into CLI flag names.
- :bug:`296 major` Don't mutate ``sys.path`` on collection load if task's
  parent directory is already on ``sys.path``.
- :bug:`295 major` Make sure that `~invoke.run`'s ``hide=True`` also disables
  echoing. Otherwise, "hidden" helper ``run`` calls will still pollute output
  when run as e.g. ``invoke --echo ...``.
- :feature:`289` (also :issue:`263`) Implement :ref:`autoresponding
  <autoresponding>` for `~invoke.run`.
- :support:`-` Removed official Python 3.2 support; sibling projects also did
  this recently, it's simply not worth the annoyance given the userbase size.
- :feature:`228` (partial) Modified and expanded implementation of
  `~invoke.executor.Executor`, `~invoke.tasks.Task` and `~invoke.tasks.Call` to
  make implementing task parameterization easier.
- :support:`-` Removed the ``-H`` short flag, leaving just ``--hide``. This was
  done to avoid conflicts with Fabric's host-oriented ``-H`` flag. Favoritism
  is real! Apologies.

  .. warning:: This change is backwards compatible if you used ``-H``.

- :feature:`173` Overhauled top level CLI functionality to allow reusing
  Invoke for distinct binaries, optionally with bundled task namespaces as
  subcommands. As a side effect, this functionality is now much more extensible
  to boot. Thanks to Erich Heine for feedback/suggestions during development.

  .. warning::
    This change is backwards incompatible if you imported anything from the
    ``invoke.cli`` module (which is now rearchitected as
    `~invoke.program.Program`). It should be transparent to everybody else.

  .. seealso:: :ref:`reusing-as-a-binary`

- :bug:`- major` Fixed a bug in the parser where ``invoke --takes-optional-arg
  avalue --anotherflag`` was incorrectly considering ``--anotherflag`` to be an
  ambiguity error (as if ``avalue`` had not been given to
  ``--takes-optional-arg``.
- :release:`0.11.1 <2015-09-07>`
- :support:`- backported` Fix incorrect changelog URL in package metadata.
- :release:`0.11.0 <2015-09-07>`
- :feature:`-` Add a ``.command`` attribute to `~invoke.runners.Result` to
  preserve the command executed for post-execution introspection.
- :feature:`-` Detect local controlling terminal size
  (`~invoke.terminals.pty_size`) and apply that information when creating
  pseudoterminals in `~invoke.run` when ``pty=True``.
- :bug:`- major` Display stdout instead of stderr in the ``repr()`` of
  `~invoke.exceptions.Failure` objects, when a pseudo-terminal was used.
  Previously, failure display focused on the stderr stream, which is always
  empty under pseudo-terminals.
- :bug:`- major` Correctly handle situations where `sys.stdin` has been
  replaced with an object lacking ``.fileno`` (e.g., some advanced Python
  shells, headless code execution tools, etc). Previously, this situation
  resulted in an ``AttributeError``.
- :bug:`- major` Capture & reraise exceptions generated by command execution I/O
  threads, in the main thread, as a `~invoke.exceptions.ThreadException`.
- :feature:`235` Allow custom stream objects to be used in `~invoke.run` calls,
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

- :bug:`234 major` (also :issue:`243`) Preserve task-module load location when
  creating explicit collections with
  `~invoke.collection.Collection.from_module`; when this was not done,
  project-local config files were not loading correctly. Thanks to ``@brutus``
  and Jan Willems for initial report & troubleshooting, and to Greg Back for
  identifying the fix.
- :bug:`237 major` Completion output lacked "inverse" flag names (e.g.
  ``--no-myoption`` as a boolean negative version of a defaulting-to-True
  boolean ``myoption``). This has been corrected.
- :bug:`239 major` Completion erroneously presented core flags instead of
  per-task flags when both are present in the invocation being completed (e.g.
  ``inv --debug my_task -<tab>``). This has been fixed.
- :bug:`238 major` (partial fix) Update the ``zsh`` completion script to
  account for use of the ``--collection`` core flag.
- :support:`-` Additional rearranging of ``run``/``Runner`` related concerns
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

- :support:`224` Add a completion script for the ``fish`` shell, courtesy of
  Jaime Marquínez Ferrándiz.
- :release:`0.10.1 <2015-03-17>`
- :support:`- backported` Tweak README to reflect recent(-ish) changes in
  ``pip`` re: users who install the development version via ``pip`` instead of
  using git.
- :release:`0.10.0 <2015-03-17>`
- :feature:`104` Add core CLI flag ``--complete`` to support shell tab
  completion scripts, and add some 'blessed' such scripts for bash (3 and 4)
  and zsh. Thanks to Ivan Malison and Andrew Roberts for providing discussion &
  early patchsets.
- :support:`-` Reorganize `~invoke.runners.Runner`, `~invoke.runners.Local` and
  ``invoke.runner.run`` for improved distribution of responsibilities &
  downstream subclassing.

  .. warning::
    This includes backwards incompatible changes to the API signature of most
    members of the ``invoke.runner`` module, including ``invoke.runner.run``.
    (However, in the case of ``invoke.runner.run``, the changes are mostly in
    the later, optional keyword arguments.)

- :feature:`219` Fall back to non-PTY command execution in situations where
  ``pty=True`` but no PTY appears present. See `~invoke.runners.Local` for
  details.
- :support:`212` Implement basic linting support using ``flake8``, and apply
  formatting changes to satisfy said linting. As part of this shakeup, also
  changed all old-style (``%s``) string formatting to new-style (``{0}``).
  Thanks to Collin Anderson for the foundational patch.
- :support:`215` (also :issue:`213`, :issue:`214`) Tweak tests & configuration
  sections of the code to include Windows compatibility. Thanks to Paul Moore.
- :bug:`201 major` (also :issue:`211`) Replace the old, first-draft gross
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

- :feature:`147` Drastically overhaul/expand the configuration system to
  account for multiple configuration levels including (but not limited to) file
  paths, environment variables, and Python-level constructs (previously the
  only option). See :ref:`configuration` for details. Thanks to Erich Heine for
  his copious feedback on this topic.

  .. warning::
    This is technically a backwards incompatible change, though some existing
    user config-setting code may continue to work as-is. In addition, this
    system may see further updates before 1.0.

- :bug:`191 major` Bypass ``pexpect``'s automatic command splitting to avoid
  issues running complex nested/quoted commands under a pty. Credit to
  ``@mijikai`` for noticing the problem.
- :bug:`183 major` Task docstrings whose first line started on the same line as
  the opening quote(s) were incorrectly presented in ``invoke --help <task>``.
  This has been fixed by using `inspect.getdoc`. Thanks to Pekka Klärck for the
  catch & suggested fix.
- :bug:`180 major` Empty invocation (e.g. just ``invoke`` with no flags or
  tasks, and when no default task is defined) no longer printed help output,
  instead complaining about the lack of default task. It now prints help again.
  Thanks to Brent O'Connor for the catch.
- :bug:`175 major` ``autoprint`` did not function correctly for tasks stored
  in sub-collections; this has been fixed. Credit: Matthias Lehmann.
- :release:`0.9.0 <2014-08-26>`
- :bug:`165 major` Running ``inv[oke]`` with no task names on a collection
  containing a default task should (intuitively) have run that default task,
  but instead did nothing. This has been fixed.
- :bug:`167 major` Running the same task multiple times in one CLI session was
  horribly broken; it works now. Thanks to Erich Heine for the report.
- :bug:`119 major` (also :issue:`162`, :issue:`113`) Better handle
  platform-sensitive operations such as pty size detection or use, either
  replacing with platform-specific implementations or raising useful
  exceptions. Thanks to Gabi Davar and (especially) Paul Moore, for feedback &
  original versions of the final patchset.
- :feature:`136` Added the ``autoprint`` flag to
  `invoke.tasks.Task`/`@task <invoke.tasks.task>`, allowing users to set up
  tasks which act as both subroutines & "print a result" CLI tasks. Thanks to
  Matthias Lehmann for the original patch.
- :bug:`162 major` Adjust platform-sensitive imports so Windows users don't
  encounter import-time exceptions. Thanks to Paul Moore for the patch.
- :support:`169` Overhaul the Sphinx docs into two trees, one for main project
  info and one for versioned API docs.
- :bug:`- major` Fixed a sub-case of the already-mostly-fixed :issue:`149` so
  the error message works usefully even with no explicit collection name given.
- :release:`0.8.2 <2014-06-15>`
- :bug:`149` Print a useful message to stderr when Invoke can't find the
  requested collection/tasks file, instead of displaying a traceback.
- :bug:`145` Ensure a useful message is displayed (instead of a confusing
  exception) when listing empty task collections.
- :bug:`142` The refactored Loader class failed to account for the behavior of
  `imp.find_module` when run against packages (vs modules) and was exploding at
  load time. This has been fixed. Thanks to David Baumgold for catch & patch.
- :release:`0.8.1 <2014-06-09>`
- :bug:`140` Revert incorrect changes to our ``setup.py`` regarding detection
  of sub-packages such as the vendor tree & the parser. Also add additional
  scripting to our Travis-CI config to catch this class of error in future.
  Thanks to Steven Loria and James Cox for the reports.
- :release:`0.8.0 <2014-06-08>`
- :feature:`135` (also bugs :issue:`120`, :issue:`123`) Implement post-tasks to
  match pre-tasks, and allow control over the arguments passed to both (via
  `invoke.tasks.call`). For details, see :ref:`pre-post-tasks`.

  .. warning::
      Pre-tasks were overhauled a moderate amount to implement this feature;
      they now require references to **task objects** instead of **task
      names**. This is a backwards incompatible change.

- :support:`25` Trim a bunch of time off the test suite by using mocking and
  other tools instead of dogfooding a bunch of subprocess spawns.
- :bug:`128 major` Positional arguments containing underscores were not
  exporting to the parser correctly; this has been fixed. Thanks to J. Javier
  Maestro for catch & patch.
- :bug:`121 major` Add missing help output denoting inverse Boolean options
  (i.e. ``--[no-]foo`` for a ``--foo`` flag whose value defaults to true.)
  Thanks to Andrew Roberts for catch & patch.
- :support:`118` Update the bundled ``six`` plus other minor tweaks to support
  files. Thanks to Matt Iversen.
- :feature:`115` Make it easier to reuse Invoke's primary CLI machinery in
  other (non-Invoke-distributed) bin-scripts. Thanks to Noah Kantrowitz.
- :feature:`110` Add task docstrings' 1st lines to ``--list`` output. Thanks to
  Hiroki Kiyohara for the original PR (with assists from Robert Read and James
  Thigpen.)
- :support:`117` Tidy up ``setup.py`` a bit, including axing the (broken)
  `distutils` support. Thanks to Matt Iversen for the original PR & followup
  discussion.
- :feature:`87` (also :issue:`92`) Rework the loader module such that recursive
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

- :support:`-` Refactor the `invoke.runners.Runner` module to differentiate
  what it means to run a command in the abstract, from execution specifics. Top
  level API is unaffected.
- :bug:`131 major` Make sure one's local tasks module is always first in
  ``sys.path``, even if its parent directory was already somewhere else in
  ``sys.path``. This ensures that local tasks modules never become hidden by
  third-party ones. Thanks to ``@crccheck`` for the early report and to Dorian
  Puła for assistance fixing.
- :bug:`116 major` Ensure nested config overrides play nicely with default
  tasks and pre-tasks.
- :bug:`127 major` Fill in tasks' exposed ``name`` attribute with body name if
  explicit name not given.
- :feature:`124` Add a ``--debug`` flag to the core parser to enable easier
  debugging (on top of existing ``INVOKE_DEBUG`` env var.)
- :feature:`125` Improve output of Failure exceptions when printed.
- :release:`0.7.0 <2014.01.28>`
- :feature:`109` Add a ``default`` kwarg to
  `invoke.collection.Collection.add_task` allowing per-collection control over
  default tasks.
- :feature:`108` Update `invoke.collection.Collection.from_module` to accept
  useful shorthand arguments for tweaking the `invoke.collection.Collection`
  objects it creates (e.g. name, configuration.)
- :feature:`107` Update configuration merging behavior for more flexible reuse
  of imported task modules, such as parameterizing multiple copies of a module
  within a task tree.
- :release:`0.6.1 <2013.11.21>`
- :bug:`96` Tasks in subcollections which set explicit names (via e.g.
  ``@task(name='foo')``) were not having those names honored. This is fixed.
  Thanks to Omer Katz for the report.
- :bug:`98` **BACKWARDS INCOMPATIBLE CHANGE!** Configuration merging has been
  reversed so outer collections' config settings override inner collections.
  This makes distributing reusable modules significantly less silly.
- :release:`0.6.0 <2013.11.21>`
- :bug:`86 major` Task arguments named with an underscore broke the help feature;
  this is now fixed. Thanks to Stéphane Klein for the catch.
- :feature:`89` Implemented configuration for distributed task modules: can set
  config options in `invoke.collection.Collection` objects and they are made
  available to contextualized tasks.
- :release:`0.5.1 <2013.09.15>`
- :bug:`81` Fall back to sane defaults for PTY sizes when autodetection gives
  insane results. Thanks to ``@akitada`` for the patch.
- :bug:`83` Fix a bug preventing underscored keyword arguments from working
  correctly as CLI flags (e.g. ``mytask --my-arg`` would not map back correctly
  to ``mytask(my_arg=...)``.) Credit: ``@akitada``.
- :release:`0.5.0 <2013.08.16>`
- :feature:`57` Optional-value flags added - e.g. ``--foo`` tells the parser to
  set the ``foo`` option value to True; ``--foo myval`` sets the value to
  "myval". The built-in ``--help`` option now leverages this feature for
  per-task help (e.g. ``--help`` displays global help, ``--help mytask``
  displays help for ``mytask`` only.)
- :bug:`55 major` A bug in our vendored copy of ``pexpect`` clashed with a
  Python 2->3 change in import behavior to prevent Invoke from running on
  Python 3 unless the ``six`` module was installed in one's environment. This
  was fixed - our vendored ``pexpect`` now always loads its sibling vendored
  ``six`` correctly.
