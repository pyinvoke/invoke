=========
Changelog
=========

* :feature:`89` Implemented configuration for distributed task modules: can set
  config options in `.Collection` objects and they are made available to
  contextualized tasks.
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
