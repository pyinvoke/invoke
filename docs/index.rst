======
Invoke
======

What is Invoke?
===============

.. include:: ../README.rst


How can I install it?
=====================

The recommended way to get Invoke is to **install the latest stable release**
via `pip <http://pip-installer.org>`_::

    $ pip install invoke

We currently support **Python 2.6/2.7** and **Python 3.3+**. Users still on
Python 2.5 or older are urged to upgrade.

As long as you have a supported Python interpreter, **there are no other
dependencies**.  Invoke is pure-Python, and contains copies of its few
dependencies within its source tree.

.. note:: 
    See `this blog post
    <http://bitprophet.org/blog/2012/06/07/on-vendorizing/>`_ for background on
    our decision to vendorize dependencies.

What if I want the bleeding edge?
---------------------------------

Users who don't intend to actively develop, but who still want to obtain the
in-development version (to help test new features or to cope with any
unfortunate lapses in release schedule) can still use ``pip``, but should give
the ``==dev`` "version" explicitly::

    $ pip install invoke==dev


How do I use it?
================

.. toctree::
    :maxdepth: 3
    :glob:

    getting_started.rst
    concepts
    api

It's broken, or doesn't do what I want! How can I submit bugs?
==============================================================

Before submitting a bug, please do the following:

* Search `the existing bug reports
  <https://github.com/pyinvoke/invoke/issues>`_ to make sure it's not a
  pre-existing issue.
* Check with :ref:`the mailing list or IRC <contact>` in case the problem is
  non-bug-related.

If you've found a new bug or thought up a new feature, please submit an issue
on our Github at `pyinvoke/invoke
<https://github.com/pyinvoke/invoke/issues>`_.

.. warning::
    Please include the following info when submitting bug reports to ensure a
    prompt response:

    * Your Python interpreter version.
    * Your operating system & version.
    * What version of Invoke you're using (& how you installed it).
    * Steps to replicate the error, if possible (including a copy of your code,
      the command you used to invoke it, and the full output of your run).


How can I contribute?
=====================

Thanks for asking! Please see our :doc:`contribution documentation
<contributing>` for details.


.. _contact:

How can I contact the developers / get help / see announcements?
================================================================

You can get in touch with the developer & user community in any of the
following ways:

* IRC: ``#invoke`` on Freenode
* Twitter: `@pyinvoke <https://twitter.com/pyinvoke>`_
* Mailing list: TK
* Blog: TK


.. toctree::
    :hidden:
    :glob:

    *
