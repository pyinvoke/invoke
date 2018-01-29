.. _autoresponding:

==========================================
Automatically responding to program output
==========================================

Background
==========

Command-line programs tend to be designed for interactive shells, which
frequently manifests as waiting around for user input, or "prompts".
Well-designed programs offer options for pre-empting such prompts, resulting in
an easily automated workflow -- but with the rest, interactivity is
unavoidable.

Thankfully, Invoke's `.Runner` class not only forwards your standard input to
the running program (allowing you to manually respond to prompts) but it can
also be configured to respond automatically on your behalf.

Basic use
=========

The mechanism for this automation is the ``watchers`` kwarg to the
`.Runner.run` method (and its wrappers elsewhere, such as `.Context.run` and
`invoke.run`), which is a list of `.StreamWatcher`-subclass instances
configured to watch for patterns & respond accordingly. The simplest of these
is `.Responder`, which just replies with its configured response every time its
pattern is seen; others can be found in the :doc:`watchers module
</api/watchers>`.

.. note::
    As with all other arguments to ``run``, you can also set the default set of
    watchers globally via :doc:`configuration files <configuration>`.

Take for example this program which expects a manual response to a yes/no
prompt::

    $ excitable-program
    When you give the OK, I'm going to do the things. All of them!!
    Are you ready? [Y/n] y
    OK! I just did all sorts of neat stuff. You're welcome! Bye!

You *could* call ``run("excitable-program")``, manually watch for the
prompt, and mash Y by hand. But if you instead supply a `.Responder` like so::

    responder = Responder(pattern=r"Are you ready? \[Y/n\] ", response="y\n")
    ctx.run("excitable-program", watchers=[responder])

Then `.Runner` passes the program's ``stdout`` and ``stderr`` through
``responder``, which watches for ``"Are you ready? [Y/n] "`` and automatically
writes ``y`` (plus ``\n`` to simulate hitting Enter/Return) to the program's
``stdin``.

.. note::
    The pattern argument to `.Responder` is treated as a `regular expression
    <re>`, requiring more care (note how we had to escape our square-brackets
    in the above example) but providing more power as well.
