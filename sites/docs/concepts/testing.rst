.. _testing-user-code:

==============================
Testing Invoke-using codebases
==============================

Strategies for testing codebases that use Invoke; some applicable to code
focused on CLI tasks, and others applicable to more generic/refactored setups.


Subclass & modify Invoke 'internals'
====================================

A quick foreword: most users will find the subsequent approaches suitable, but
advanced users should note that Invoke has been designed so it is itself easily
testable. This means that in many cases, even Invoke's "internals" are exposed
as low/no-shared-responsibility, publicly documented classes which can be
subclassed and modified to inject test-friendly values or mocks. Be sure to
look over the :ref:`API documentation <api>`!


Use `.MockContext`
==================

An instance of subclassing Invoke's public API for test purposes is our own
`.MockContext`. Codebases which revolve heavily around `.Context` objects and
their methods (most task-oriented code) will find it easy to test by injecting
`.MockContext` objects which have been instantiated to yield partial `.Result`
objects.

For example, take this task::

    from invoke import task

    @task
    def get_platform(c):
        uname = c.run("uname -s").stdout.strip()
        if uname == 'Darwin':
            return "You paid the Apple tax!"
        elif uname == 'Linux':
            return "Year of Linux on the desktop!"

An example of testing it with `.MockContext` could be the following::

    from invoke import MockContext, Result
    from mytasks import get_platform

    def test_get_platform_on_mac():
        c = MockContext(run=Result("Darwin\n"))
        assert "Apple" in get_platform(c)

    def test_get_platform_on_linux():
        c = MockContext(run=Result("Linux\n"))
        assert "desktop" in get_platform(c)

Putting the ``Mock`` in `.MockContext`
--------------------------------------

Starting in Invoke 1.5, `.MockContext` will attempt to import the ``mock``
library at instantiation time and wrap its methods within ``Mock`` objects.
This lets you not only present realistic return values to your code, but make
test assertions about what commands your code is running.

Here's another "platform sensitive" task::

    from invoke import task

    @task
    def replace(c, path, search, replacement):
        # Assume systems have sed, and that some (eg macOS w/ Homebrew) may
        # have gsed, implying regular sed is BSD style.
        has_gsed = c.run("which gsed", warn=True, hide=True)
        # Set command to run accordingly
        binary = "gsed" if has_gsed else "sed"
        c.run(f"{binary} -e 's/{search}/{replacement}/g' {path}")

The test code (again, which presumes that eg ``MockContext.run`` is now a
``Mock`` wrapper) relies primarily on 'last call' assertions
(``Mock.assert_called_with``) but you can of course use any ``Mock`` methods
you need. It also shows how you can set the mock context to respond to multiple
possible commands, using a dict value::

    from invoke import MockContext, Result
    from mytasks import replace

    def test_regular_sed():
        expected_sed = "sed -e s/foo/bar/g file.txt"
        c = MockContext(run={
            "which gsed": Result(exited=1),
            expected_sed: Result(),
        })
        replace(c, 'file.txt', 'foo', 'bar')
        c.run.assert_called_with(expected_sed)

    def test_homebrew_gsed():
        expected_sed = "gsed -e s/foo/bar/g file.txt"
        c = MockContext(run={
            "which gsed": Result(exited=0),
            expected_sed: Result(),
        })
        replace(c, 'file.txt', 'foo', 'bar')
        c.run.assert_called_with(expected_sed)

Boolean mock results
--------------------

You may have noticed the above example uses a handful of 'empty' `.Result`
objects; these stand in for "succeeded, but otherwise had no useful attributes"
command executions (as `.Result` defaults to an exit code of ``0`` and empty
strings for stdout/stderr).

This is relatively common - think "interrogative" commands where the caller
only cares for a boolean result, or times when a command is called purely for
its side effects. To support this, there's a shorthand in `.MockContext`:
passing ``True`` or ``False`` to stand in for otherwise blank Results with exit
codes of ``0`` or ``1`` respectively.

The example tests then look like this::

    from invoke import MockContext, Result
    from mytasks import replace

    def test_regular_sed():
        expected_sed = "sed -e s/foo/bar/g file.txt"
        c = MockContext(run={
            "which gsed": False,
            expected_sed: True,
        })
        replace(c, 'file.txt', 'foo', 'bar')
        c.run.assert_called_with(expected_sed)

    def test_homebrew_gsed():
        expected_sed = "gsed -e s/foo/bar/g file.txt"
        c = MockContext(run={
            "which gsed": True,
            expected_sed: True,
        })
        replace(c, 'file.txt', 'foo', 'bar')
        c.run.assert_called_with(expected_sed)

String mock results
-------------------

Another convenient shorthand is using string values, which are interpreted to
be the stdout of the resulting `.Result`. This only really saves you from
writing out the class itself (since ``stdout`` is the first positional arg of
`.Result`!) but "command X results in stdout Y" is a common enough use case
that we implemented it anyway.

By example, let's modify an earlier example where we cared about stdout::

    from invoke import MockContext
    from mytasks import get_platform

    def test_get_platform_on_mac():
        c = MockContext(run="Darwin\n")
        assert "Apple" in get_platform(c)

    def test_get_platform_on_linux():
        c = MockContext(run="Linux\n")
        assert "desktop" in get_platform(c)

As with everything else in this document, this tactic can be applied to
iterators or mappings as well as individual values.

Regular expression command matching
-----------------------------------

The dict form of `.MockContext` kwarg can accept regular expression objects as
keys, in addition to strings; ideal for situations where you either don't know
the exact command being invoked, or simply don't need or want to write out the
entire thing.

Imagine you're writing a function to run package management commands on a few
different Linux distros and you're trying to test its error handling. You might
want to set up a context that pretends any arbitrary ``apt`` or ``yum`` command
fails, and ensure the function returns stderr when it encounters a problem::

    import re
    from invoke import MockContext
    from mypackage.tasks import install

    package_manager = re.compile(r"^(apt(-get)?|yum) .*")

    def test_package_success_returns_True():
        c = MockContext(run={package_manager: True})
        assert install(c, package="somepackage") is True

    def test_package_explosions_return_stderr():
        c = MockContext(run={
            package_manager: Result(stderr="oh no!", exited=1),
        })
        assert install(c, package="otherpackage") == "oh no!"

A bit contrived - there are a bunch of other ways to organize this exact test
code so you don't truly need the regex - but hopefully it's clear that when you
*do* need this flexibility, this is how you could go about it.

Repeated results
----------------

By default, the values in these mock structures are consumed, causing
`.MockContext` to raise ``NotImplementedError`` afterwards (as it does for any
unexpected command executions). This was designed with the assumption that
most code under test will run a given command once.

If your situation doesn't match this, give ``repeat=True`` to the constructor,
and you'll see values repeat indefinitely instead (or in cycles, for
iterables).


Expect `Results <.Result>`
==========================

The core Invoke subprocess methods like `~.Context.run` all return `.Result`
objects - which (as seen above) can be readily instantiated by themselves with
only partial data (e.g. standard output, but no exit code or standard error).

This means that well-organized code can be even easier to test and doesn't
require as much use of `.MockContext`.

An iteration on the initial `.MockContext`-using example above::

    from invoke import task

    @task
    def get_platform(c):
        print(platform_response(c.run("uname -s")))

    def platform_response(result):
        uname = result.stdout.strip()
        if uname == 'Darwin':
            return "You paid the Apple tax!"
        elif uname == 'Linux':
            return "Year of Linux on the desktop!"

With the logic encapsulated in a subroutine, you can just unit test that
function by itself, deferring testing of the task or its context::

    from invoke import Result
    from mytasks import platform_response

    def test_platform_response_on_mac():
        assert "Apple" in platform_response(Result("Darwin\n"))

    def test_platform_response_on_linux():
        assert "desktop" in platform_response(Result("Linux\n"))


Avoid mocking dependency code paths altogether
==============================================

This is more of a general software engineering tactic, but the natural endpoint
of the above code examples would be where your primary logic doesn't care about
Invoke at all -- only about basic Python (or locally defined) data types. This
allows you to test logic in isolation and either ignore testing the Invoke side
of things, or write targeted tests solely for where your code interfaces with
Invoke.

Another minor tweak to the task code::

    from invoke import task

    @task
    def show_platform(c):
        uname = c.run("uname -s").stdout.strip()
        print(platform_response(uname))

    def platform_response(uname):
        if uname == 'Darwin':
            return "You paid the Apple tax!"
        elif uname == 'Linux':
            return "Year of Linux on the desktop!"

And the tests::

    from mytasks import platform_response

    def test_platform_response_on_mac():
        assert "Apple" in platform_response("Darwin\n")

    def test_platform_response_on_linux():
        assert "desktop" in platform_response("Linux\n")
