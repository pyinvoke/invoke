==========
Installing
==========

Basic installation
==================

The recommended way to get Invoke is to **install the latest stable release**
via `pip <https://pip.pypa.io>`_::

    $ pip install invoke

We currently support **Python 3.9+**. Users still on Python 3.8 or older are
urged to upgrade.

As long as you have a supported Python interpreter, **there are no other
dependencies**.  Invoke is pure-Python, and contains copies of its few
dependencies within its source tree.

.. note:: 
    See `this blog post
    <https://bitprophet.org/blog/2012/06/07/on-vendorizing/>`_ for background on
    our decision to vendorize dependencies.

.. seealso::
    :doc:`development` for details on source control checkouts / unstable
    versions.
