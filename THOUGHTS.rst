==============================================
Random thoughts unsuitable for public docs yet
==============================================

CLI type mapping
================

Some loose thoughts on bridging the "shell is strings, Python wants
lists/dicts/integers/bools/etc" problem.

Methodologies
-------------

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
  E.g. we could say that commas in an argument automatically trigger
  transformation into a list of strings; thus the invocation::

    $ invoke mytask --items a,b,c

  would on the Python end turn into a call like this::

    mytask(items=['a', 'b', 'c'])

What to do?
~~~~~~~~~~~

We haven't decided exactly how many of these to use -- we may end up using all
three of them as appropriate, with some useful/sensible default and the option
to enable/disable things for power users. The trick is to balance
power/features with becoming overly complicated to understand or utilize.

Other types
-----------

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


Parameterizing tasks
====================

Old "previous example" (at time the below was split out of live docs, the
actual previous example had been changed a lot and no longer applied)::

    $ invoke test --module=foo test --module=bar
    Cleaning
    Testing foo
    Cleaning
    Testing bar

The previous example had a bit of duplication in how it was invoked; an
intermediate use case is to bundle up that sort of parameterization into a
"meta" task that itself invokes other tasks in a parameterized fashion.

TK: API for this? at CLI level would have to be unorthodox invocation, e.g.::

    @task
    def foo(bar):
        print(bar)

    $ invoke --parameterize foo --param bar --values 1 2 3 4
    1
    2
    3
    4

Note how there's no "real" invocation of ``foo`` in the normal sense. How to
handle partial application (e.g. runtime selection of other non-parameterized
arguments)? E.g.::

    @task
    def foo(bar, biz):
        print("%s %s" % (bar, biz))

    $ invoke --parameterize foo --param bar --values 1 2 3 4 --biz "And a"
    And a 1
    And a 2
    And a 3
    And a 4

That's pretty clunky and foregoes any multi-task invocation. But how could we
handle multiple tasks here? If we gave each individual task flags for this,
like so::

    $ invoke foo --biz "And a" --param foo --values 1 2 3 4

We could do multiple tasks, but then we're stomping on tasks' argument
namespaces (we've taken over ``param`` and ``values``). Really hate that.

**IDEALLY** we'd still limit parameterization to library use since it's an
advanced-ish feature and frequently the parameterization vector is dynamic (aka
not the sort of thing you'd give at CLI anyway)

Probably best to leave that in the intermediate docs and keep it lib level;
it's mostly there for Fabric and advanced users, not something the average
Invoke-only user would care about. Not worth the effort to make it work on CLI
at this point.

::

    @task
    def stuff(var):
        print(var)

    # NOTE: may need to be part of base executor since Collection has to know
    # to pass the parameterization option/values into Executor().execute()?
    class ParameterizedExecutor(Executor):
        # NOTE: assumes single dimension of parameterization.
        # Realistically would want e.g. {'name': [values], ...} structure and
        # then do cross product or something
        def execute(self, task, args, kwargs, parameter=None, values=None):
            # Would be nice to generalize this?
            if parameter:
                # TODO: handle non-None parameter w/ None values (error)
                # NOTE: this is where parallelization would occur; probably
                # need to move into sub-method
                for value in values:
                    my_kwargs = dict(kwargs)
                    my_kwargs[parameter] = value
                    super(self, ParameterizedExecutor).execute(task, kwargs=my_kwargs)
            else:
                super(self, ParameterizedExecutor).execute(task, args, kwargs)


Getting hairy: one task, with one pre-task, parameterized
=========================================================

::

    @task
    def setup():
        print("Yay")

    @task(pre=[setup])
    def build():
        print("Woo")

    class OhGodExecutor(Executor):
        def execute(self, task, args, kwargs, parameter, values):
            # assume always parameterized meh
            # Run pretasks once only, instead of once per parameter value
            for pre in task.pre:
                self.execute(self.collection[pre])
            for value in values:
                my_kwargs = dict(kwargs)
                my_kwargs[parameter] = value
                super(self, OhGodExecutor).execute(task, kwargs=my_kwargs)


Still hairy: one task, with a pre-task that itself has a pre-task
=================================================================

All the things: two tasks, each with pre-tasks, both parameterized
==================================================================
