===========
Development
===========

Obtaining a source checkout
===========================

Our Git repository is maintained on Github at `pyinvoke/invoke`_. Please
follow their instructions for cloning (or forking, then cloning, which is best
if you intend to contribute back) the repository there.

Once downloaded, install the repo itself + its development dependencies by
running ``pip install -r dev-requirements.txt``.


Submitting bug reports or patches
=================================

We follow `contribution-guide.org`_ for all of our development - please `go
there`_ for details on submitting patches, which branch(es) to work out of,
and so on. Our issue tracker is on `our GitHub page`_.


Running management tasks
========================

Invoke uses itself for project management and has a number of tasks you can
see with ``inv --list``. Some specific tasks of note:

    * ``test`` and ``integration``: Runs the primary and integration test
      suites, respectively. (Most of the time you can ignore ``integration`` -
      it's mostly for use by CI systems or once-in-a-while sanity checks
      locally.)
    * ``www`` and ``docs`` (and their subtasks like ``docs.browse``): Builds
      the WWW site and the API docs, respectively.


.. _go there:
.. _contribution-guide.org: http://contribution-guide.org

.. _our GitHub page:
.. _pyinvoke/invoke: https://github.cm/pyinvoke/invoke
