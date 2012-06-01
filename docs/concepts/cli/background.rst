==========
Background
==========

Command-line invocation interfaces are surprisingly complicated, and Invoke's
needs are also a little on the unique side. This document tries to outline the
various possible approaches and why Invoke ended up with the mechanism it
currently provides.

Basics
======

Flags/options, and arguments given to them, are pretty universal::

    $ invoke --boolean
    $ invoke --takes-arg thearg
    $ invoke --takes-arg=thearg
    $ invoke -s
    $ invoke -s sarg

Using "standard" GNU style long and short flags is a no-brainer. A less common
syntax is "Java style" where verbose/long flags can be given with a single
dash::

    $ java -jar path/to/jar

We're not a fan of this style so it was never under consideration.

Short flag peculiarities
------------------------

Short flags tend to vary a bit more, re: whether an equals sign is allowed
(``program -f=bar``), and sometimes even whether a space is required (``tail
-n5``).

There's also combined short flags (``tar -xzv`` standing in for ``tar -x -z
-v``) which only work for boolean options as they'd be ambiguous otherwise (are
the 2nd through Nth characters other combined short flags, or are they the
argument to the 1st short flag?)

For the time being, we've gone with "equals sign optional" and for keeping
combined flags as a "nice-to-have" feature we may add in later on (but not
worth tackling right away.)


The multiple tasks vs positional args problem
=============================================

This is the meat. Invoke really wanted to have multiple tasks in the spirit of
Fabric 1.x, which supported invocations like::

    $ fab task1:arg1,arg2=val2 task2:args

though we didn't want to continue using that specific invoke style. Instead we
wanted something that looked like this::

    $ invoke --global-opts task1 --task1-opts task2 --task2-opts [...]

Unfortunately ``argparse`` and friends are unable to do this, because they:

* have no way of "partitioning" input, so all flags/options get lumped
  together; and
* consider any non-flag input to be "positional arguments" and toss them into a
  simple list with no way to tell where they showed up in the original
  invocation.

That leaves us on our own.

The naive approach
------------------

The main hurdle here is being able to tell when one task's "chunk" of the input
ends and another begins. In a really simple use case, we could just say
"anything that's not a flag is a task name". Our earlier example, repeated
below, is exactly that simple::

    $ invoke --global-opts task1 --task1-opts task2 --task2-opts [...]

Using the "not a flag" heuristic above gives us nicely delineated chunks to
perhaps hand off to some ``argparse`` based sub-parsers.

Unfortunately, this breaks down as soon as you get into non-boolean options
(i.e. options that have their own arguments.) E.g. what if ``task1`` can be
parameterized by some ``kwarg`` that takes a value::

    $ invoke --global-opts task1 --kwarg value task2

In this case, our naive parser will think ``value`` is a task name, when it's
actually supposed to be parameterizing ``kwarg``. Not good!

Telling tasks apart
-------------------

There are multiple ways to solve this problem and tell tasks apart from flag
arguments, each with pluses/minuses:

* Give the parser deep knowledge of the flags involved so that when it
  encounters ``--flag value task`` it knows that ``--flag`` is supposed to have
  a value after it. This can be done explicitly (think ``argparse`` style
  argument definitions) or can be inferred from the task definition.
  
    * Unfortunately, we can't use ``argparse`` or ``optparse`` to do this as
      they are unable to cope with various potential edge cases that arise in a
      multi-task situation.
      
    * For example, while ``optparse`` is capable of being told to stop at the
      first unknown positional arg (in our case, the next task name) and could
      be used in a loop, it still thinks about the flags it encounters
      globally. Two tasks using the same keyword argument name would make
      setting up an ``optparse`` parser impossible. Requiring globally unique
      kwarg names would solve this, but is too user-hostile.

* Force users to avoid using spaces between flags and their arguments, i.e.
  always doing ``--flag=value`` or ``-fvalue``. This makes tasks unambiguous,
  at the cost of cutting out a very common technique in other CLI tools' flag
  styles. This is also unacceptable as it falls into the trap of looking very
  similar to, but not behaving like, regular flags.
* Add special syntax to denote task names, e.g.::

    $ invoke --global-opts task1: --kwarg value task2: --task2-opts

  where the trailing colon is a sign that that particular "word" is a task
  name. This is unorthodox but not terrifically ugly and could ease parsing.
* Alternately, use standalone sentinel characters in-between the task/arg
  "chunks" which have no special shell meaning, e.g.::

    $ invoke --global-opts , task1 --kwarg value , task2 --task2-opts , [...]

  While this would be the simplest to parse, it's also pretty unappealing.

Per-task positional args
~~~~~~~~~~~~~~~~~~~~~~~~

An additional benefit of the second two approaches above is that they would
enable support for per-task positional arguments, e.g.::

    $ invoke --global-opts task1: arg1 arg2 --kwarg=value task2: --kwarg2=value2

The first approach is unable to do this without adding even more complexity to
both the user-facing task signature specification, and to the parser.


Ambiguities
===========

A discussion on some potential ambiguities which arise in most styles of
argument parsing.

Space-delimited flag values that look like flags themselves
-----------------------------------------------------------

I.e.::

    $ invoke --takes-a-value --some-other-valid-flag

The above can be interpreted in two ways:

* ``--takes-a-value`` having its value set to ``"--some-other-flag"``
    * Pluses: allows specifying flag-like values, which would otherwise have to
      be escaped in some fashion.
    * Minuses: can obscure user error.
* ``--some-other-valid-flag`` being interpreted as an actual flag, and an error
  being generated because ``--takes-a-value`` is then missing a value.
    * Has the inverse tradeoff to the above: fast-fails on user error, but
      would require escaping for actual flag-like values to be treated as flag
      arguments.

A related issue is the possibility of **invalid** flag-like values, e.g.::

    $ invoke --takes-a-value --not-even-a-valid-flag

This doesn't even make sense in the 2nd approach above, because now we've both
got a "missing value" error *and* a "unknown flag" error, whereas the 1st
approach still works as the user probably intended.
