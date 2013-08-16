=========
Changelog
=========

Temporary changelog until we get something multi-branch-aware working.

0.5.0 (2013.08.16)
==================

* Optional-value flags added - e.g. ``--foo`` tells the parser to set the
  ``foo`` option value to True; ``--foo myval`` sets the value to
  "myval".
* The core ``--help`` option now leverages optional-value flags and will
  display per-task help if a task name is given.
* A bug in our vendored copy of ``pexpect`` clashed with a Python 2->3
  change in import behavior to prevent Invoke from running on Python 3 unless
  the ``six`` module was installed in one's environment. This was fixed - our
  vendored ``pexpect`` now always loads its sibling vendored ``six`` correctly.
