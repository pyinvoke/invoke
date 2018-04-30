.. _loading-collections:

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
Python module or package named ``tasks``, and will treat it as the root
namespace. ``tasks`` (or any other name given via :ref:`loading configuration
options <configuring-loading>`) is searched for in the following ways:

* First, if a valid tasks module by that name already exists on Python's
  `sys.path <http://docs.python.org/release/2.7/library/sys.html#sys.path>`_,
  no more searching is done -- that module is selected.
* Failing that, search towards the root of the local filesystem, starting with
  the user's current working directory (`os.getcwd
  <http://docs.python.org/release/2.7/library/os.html#os.getcwd>`_) and try
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


.. _configuring-loading:

Configuring the loading process
===============================

You can configure the above behavior, requesting that Invoke alter the
collection name searched for and/or the path where filesystem-level loading
starts looking.

For example, you may already have a project-level ``tasks.py`` that you can't
easily rename; or you may want to host a number of tasks collections stored
outside the project root and make it easy to switch between them; or any number
of reasons.

Both the sought collection name and the search root can be specified via
:ref:`configuration file options <config-files>` or as :doc:`runtime CLI flags
</invoke>`:

- **Change the collection name**: Set the ``tasks.collection_name``
  configuration option, or use :option:`--collection`. It should be a Python
  module name and not a file name (so ``mytasks``, not ``mytasks.py`` or
  ``mytasks/``.)
- **Change the root search path**: Configure ``tasks.search_root`` or use
  :option:`--search-root`. This value may be any valid directory path.
