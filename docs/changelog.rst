=========
Changelog
=========

* :feature:`110` Add task docstrings' 1st lines to ``--list`` output. Thanks to
  Hiroki Kiyohara for the original PR (with assists from Robert Read and James
  Thigpen.)
* :support:`117` Tidy up ``setup.py`` a bit, including axing the (broken)
  `distutils` support. Thanks to Matt Iverson for the original PR & followup
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

* :support:`-` Refactor the `.Runner` module to differentiate what it means to
  run a command in the abstract, from execution specifics. Top level API is
  unaffected.
* :bug:`131` Make sure one's local tasks module is always first in
  ``sys.path``, even if its parent directory was already somewhere else in
  ``sys.path``. This ensures that local tasks modules never become hidden by
  third-party ones. Thanks to ``@crccheck`` for the early report and to Dorian
  Puła for assistance fixing.
* :bug:`116` Ensure nested config overrides play nicely with default tasks and
  pre-tasks.
* :bug:`127` Fill in tasks' exposed ``name`` attribute with body name if
  explicit name not given.
* :feature:`124` Add a ``--debug`` flag to the core parser to enable easier
  debugging (on top of existing ``INVOKE_DEBUG`` env var.)
* :feature:`125` Improve output of Failure exceptions when printed.
* :release:`0.7.0 <2014.01.28>`
* :feature:`109` Add a ``default`` kwarg to `.Collection.add_task` allowing
  per-collection control over default tasks.
* :feature:`108` Update `.from_module` to accept useful shorthand arguments for
  tweaking the `.Collection` objects it creates (e.g. name, configuration.)
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
  config options in `.Collection` objects and they are made available to
  contextualized tasks. See :ref:`configuration`.
* :release:`0.5.1 <2013.09.15>`
* :bug:`81` Fall back to sane defaults for PTY sizes when autodetection gives
  insane results. Thanks to `@akitada` for the patch.
* :bug:`83` Fix a bug preventing underscored keyword arguments from working
  correctly as CLI flags (e.g. ``mytask --my-arg`` would not map back correctly
  to ``mytask(my_arg=...)``.) Credit: `@akitada`.
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
