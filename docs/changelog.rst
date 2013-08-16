=========
Changelog
=========

Temporary changelog until we get something multi-branch-aware working.

0.5.0 (2013.08.16)
==================

* Optional-value flags added - e.g. ``--help`` tells the parser to set the
  ``help`` option value to True; ``--help sometask`` sets the value to
  "sometask".
* The core ``--help`` option now leverages optional-value flags and will
  display per-task help if a task name is given.
* A bug in our vendored copy of ``pexpect`` clashed with a Python 2->3
  change in import behavior to prevent Invoke from running on Python 3 unless
  the ``six`` module was installed in one's environment. This was fixed - our
  vendored ``pexpect`` now always loads its sibling vendored ``six`` correctly.
