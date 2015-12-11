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

By default, Invoke's `.Runner` class attaches your local ``stdin`` to the
program's, letting you interact with prompts directly. That's fine for cases
where you truly want a human at the wheel -- but because Invoke is sitting
between you and the program, it can act on your behalf, similar to the
``expect`` program or its emulations like `pexpect
<https://pexpect.readthedocs.org>`_.

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

Then `.Runner` will monitor the program's ``stdout`` and ``stderr`` for
the existence of ``"Are you ready? [Y/n] "`` and automatically write
``"y\n"`` to its ``stdin`` on your behalf.

.. note::
    Keep in mind that ``responses`` keys are treated as `regular expressions
    <re>`, which requires more care (note how we had to escape our
    square-brackets in the above example) but provides more power as well.

Subclasses of `.Runner` may extend this functionality further, for example
auto-responding to password prompts (as seen in `Fabric
<http://fabfile.org>`_).
