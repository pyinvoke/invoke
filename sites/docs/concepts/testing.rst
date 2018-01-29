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
    def show_platform(c):
        uname = c.run("uname -s").stdout.strip()
        if uname == 'Darwin':
            print("You paid the Apple tax!")
        elif uname == 'Linux':
            print("Year of Linux on the desktop!")

An example of testing it with `.MockContext` could be the following (note:
``trap`` is only one example of a common test framework tactic which mocks
``sys.stdout``/``err``)::

    import sys
    from spec import trap
    from invoke import MockContext, Result
    from mytasks import show_platform

    @trap
    def test_show_platform_on_mac():
        c = MockContext(run=Result("Darwin\n"))
        show_platform(c)
        assert "Apple" in sys.stdout.getvalue()

    @trap
    def test_show_platform_on_linux():
        c = MockContext(run=Result("Linux\n"))
        show_platform(c)
        assert "desktop" in sys.stdout.getvalue()


Expect `Results <.Result>`
==========================

The core Invoke subprocess methods like `~.Context.run` all return `.Result`
objects - which (as seen above) can be readily instantiated by themselves with
only partial data (e.g. standard output, but no exit code or standard error).

This means that well-organized code can be even easier to test and doesn't
require as much use of `.MockContext` or terminal output mocking.

An iteration on the previous example::

    from invoke import task

    @task
    def show_platform(c):
        print(platform_response(c.run("uname -s")))

    def platform_response(result):
        uname = result.stdout.strip()
        if uname == 'Darwin':
            return "You paid the Apple tax!"
        elif uname == 'Linux':
            return "Year of Linux on the desktop!"

Now the bulk of the actual logic is testable with fewer lines of code and fewer
assumptions about the "real world" the code runs within::

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
