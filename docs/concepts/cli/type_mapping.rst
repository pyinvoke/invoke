============
Type mapping
============

Some loose thoughts on bridging the "shell is strings, Python wants
lists/dicts/integers/bools/etc" problem.

Methodologies
=============

* Explicit mapping, as with ``argparse``: this particular flag turns into a
  list/boolean/int/whatever. Because we're specifically mapping to function
  keyword arguments, a little of that complexity can be removed, but generally
  it'll look very similar. E.g.::

    @args(foo=int)
    def mytask(foo):
        ...

  would turn this::

    $ invoke mytask --foo 7

  into ``7``, not ``"7"``.
* Introspection-based mapping, i.e. introspecting the default values of a
  function signature and automatically transforming the CLI input. E.g.::

    def mytask(foo=5):
        ...

  invoked as::

    $ invoke mytask --foo 7

  results in the Python value ``7`` instead of ``"7"``, just as with the
  explicit example above.
* Formatting-based mapping, i.e. having (optional) conventions in the string
  format of an incoming flag argument that cause transformations to occur.
  E.g. the invocation::

    $ invoke mytask --items a,b,c

  would on the Python end turn into a call like this::

    mytask(items=['a', 'b', 'c'])

What to do?
-----------

We haven't decided exactly how many of these to use -- we may end up using all
three of them as appropriate, with some useful/sensible default and the option
to enable/disable things for power users. The trick is to balance
power/features with becoming overly complicated to understand or utilize.

Other types
===========

Those examples cover integers/numbers, and lists/iterables. Strings are
obviously easy/the default. What else is there?

* Booleans: these are relatively simple too, either a flag exists (``True``) or
  is omitted (``False``).
  
    * Could also work in a ``--foo`` vs ``--no-foo`` convention to help with
      the inverse, i.e. values which should default to ``True`` and then need
      to be turned "off" on the command line. E.g.::

        def mytask(option=True):
            ...

      could result in having a flag called ``--no-option`` instead of
      ``--option``. (Or possibly both.)

* Dicts: these are tougher, but we could potentially use something like::

    $ invoke mytask --dictopt key1=val1,key2=val2

  resulting in::

    mytask(dictopt={'key1': 'val1', 'key2': 'val2'})
