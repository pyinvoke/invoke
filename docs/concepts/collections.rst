=========================
Creating task collections
=========================

* Directly, by subclassing Collection and defining methods on that class.
* Indirectly, via a Python module/package containing module-level functions.
* In either situation, use of ``@task`` is required to explicitly denote tasks.
* ``@task`` does not replace the original decorated callable, but simply flags
  it as a valid task (as well as noting other options possibly selected in
  ``@task`` arguments.)
* Collection creation then wraps these designated callables inside richer
  objects.
