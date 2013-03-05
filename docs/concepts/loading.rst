===================
Loading collections
===================

The core of Invoke's execution model involves one or more Collection objects.
While these may be created programmatically, in typical use Invoke will create
them for you from Python modules it finds or is told to use.


.. _collection-discovery:

Task module discovery
=====================

With no other configuration, simply calling ``invoke`` will look for a single
Python module named ``tasks``, and will treat it as the root namespace.
``tasks`` (and any other module name given via :ref:`the load options
<load-options>`) is searched for in the following ways:

* First, if a valid tasks module by that name already exists on Python's
  `sys.path <http://docs.python.org/release/2.6.7/library/sys.html#sys.path>`_,
  no more searching is done -- that module is selected.
* Failing that, search towards the root of the local filesystem, starting with
  the user's current working directory (`os.getcwd
  <http://docs.python.org/release/2.6.7/library/os.html#os.getcwd>`_) and try
  importing again with each directory temporarily added to ``sys.path``.

    * Due to how Python's import machinery works, this approach will always
      favor a package directory (``tasks/`` containing an ``__init__.py``) over
      a module file (``tasks.py``) in the same location.
    * If a candidate is found and successfully imported, its parent directory
      will **stay** on ``sys.path`` during the rest of the Python session --
      this allows task code to make convenient assumptions concerning sibling
      modules' importability.

Candidate modules/packages are introspected to make sure they can actually be
used as valid task collections. Any that fail are discarded, the ``sys.path``
munging done to import them is reverted, and the search continues.


.. _load-options:

Additional load options
=======================

The ``-c`` / ``--collection`` command-line argument allows you to override the
default collection name searched for. It should be a Python module name and not
a file name (so ``-c mytasks``, not ``-c mytasks.py`` or ``-c mytasks/``.) This
option is repeatable and may be used to load multiple collections at runtime.

.. note::
    When multiple collections are specified, the first collection given will be
    used as the root or default namespace. The rest will be attached to it as
    sub-collections. See :doc:`namespaces` for details.

If you need to override the default search start point so Invoke no longer
searches from the current directory, use ``--root``. E.g. if your tasks module
is in ``/opt/code/myproject/tasks.py`` and your CWD is, say, ``/home/myuser``,
you might run Invoke as::

    $ invoke --root /opt/code/myproject
