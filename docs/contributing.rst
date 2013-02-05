======================
Contributing to Invoke
======================

How to get the code
===================

Our primary Git repository is on Github at `pyinvoke/invoke
<https://github.com/pyinvoke/invoke>`; please follow their instruction for
cloning to your local system. (If you intend to submit patches/pull requests,
we recommend forking first, then cloning your fork. Github has excellent
documentation for all this.)

Development guidelines
======================

.. warning::
    Please follow these instructions closely! Your patch will not be accepted
    (or will at least be delayed) otherwise. Thanks!

Which branch to work out of
---------------------------

We split development into two primary branches:

* **Bug fixes** go into a branch named after the **current stable release
  line** (e.g. 1.0, 1.1, 1.2 etc).

    * Caveat: bug fixes requiring large changes to the code or which have a
      chance of being otherwise disruptive, may need to go in **master**
      instead. This is a judgement call -- ask the devs!

* **New features** go into **the master branch**.

    * Note that depending on how long it takes for the dev team to merge your
      patch, the copy of ``master`` you worked off of may get out of date! If
      you find yourself 'bumping' a pull request that's been sidelined for a
      while, **make sure you rebase or merge to latest master** to ensure a
      speedier resolution.

Code formatting
---------------

We follow `PEP-8 <http://www.python.org/dev/peps/pep-0008/>`_ whenever it makes
sense, which is most of the time. At the very least, please make sure you put
spaces after your commas within list-like syntax (``[this,is,not,ok]`` but
``[this, is, fine]``; ditto for ``function(calls, like, this)``) and keep your
variables ``lower_cased_and_underscored``, with only classes being
``CamelCased``.

Documentation isn't optional
----------------------------

It's not! Patches without documentation will be returned to sender.
Specifically, by "documentation" we mean:

* **Docstrings** must be created or updated for public API
  functions/methods/etc.

    * Don't forget to include `versionadded
      <http://sphinx-doc.org/markup/para.html#directive-versionadded>`_/`versionchanged
      <http://sphinx-doc.org/markup/para.html#directive-versionchanged>`_ ReST
      directives at the bottom of any new or changed docstrings!
    * Use ``versionadded`` for truly new API members -- new methods, functions,
      classes or modules.
    * Use ``versionchanged`` when adding/removing new function/method
      arguments, or whenever behavior changes.

* New features should ideally include updates to **prose documentation**,
  including useful example code snippets.
* All changes (**including bugfixes**) should have a **changelog entry**
  crediting the contributor and/or any individuals instrumental in identifying
  the problem.

Tests aren't optional
---------------------

We aim for very high code coverage. Any bugfix that doesn't include a test
proving the existence of the bug being fixed (and of course, that passes when
the bugfix is applied) may be suspect.

We've found that test-first development really helps make features better
architected and identifies potential edge cases earlier instead of later. New
features should also include thorough tests.
