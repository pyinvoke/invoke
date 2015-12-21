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

The mechanism for this automation is the ``responses`` kwarg to the
`.Runner.run` method (and its wrappers elsewhere, such as `.Context.run` and
`invoke.run`), which is simply a dict mapping expected patterns to their
responses.

Take for example this mock shell session::

    $ excitable-program
    When you give the OK, I'm going to do the things. All of them!!
    Are you ready? [Y/n] y
    OK! I just did all sorts of neat stuff. You're welcome! Bye!

You *could* simply call ``run("excitable-program")``, manually watch for the
prompt, and mash Y by hand. But if you instead supply ``responses`` like so::

    responses = {r"Are you ready? \[Y/n\] ": "y\n"}
    run("excitable-program", responses=responses)

Then `.Runner` will monitor the program's ``stdout`` and ``stderr`` for the
existence of ``"Are you ready? [Y/n] "`` and automatically write ``y`` (plus
``\n`` to simulate hitting Enter/Return) to its ``stdin``.

.. note::
    Keep in mind that ``responses`` keys are treated as `regular expressions
    <re>`, which requires more care (note how we had to escape our
    square-brackets in the above example) but provides more power as well.

Subclasses of `.Runner` may extend this functionality further, for example
auto-responding to specific password prompts.
