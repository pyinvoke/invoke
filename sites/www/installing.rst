==========
Installing
==========

Basic installation
==================

The recommended way to get Invoke is to **install the latest stable release**
via `pip <https://pip.pypa.io>`_ or `uv <https://docs.astral.sh/uv/>`_, eg::

    $ pip install invoke

As long as you have a supported Python interpreter (defined in the repository's
`pyproject.toml <https://github.com/pyinvoke/invoke/tree/main/pyproject.toml>`_
and reflected on our `PyPI page <https://pypi.org/project/invoke/>`_), **there
are no other dependencies**.  Invoke is pure-Python, and contains copies of its
few dependencies within its source tree.

.. note:: 
    See `this blog post
    <https://bitprophet.org/blog/2012/06/07/on-vendorizing/>`_ for background on
    our decision to vendorize dependencies.

.. seealso::
    :doc:`development` for details on source control checkouts / unstable
    versions.
