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

Design rationale
================

.. warning::
    For reasons outlined below, **multiline patterns cannot be used in the
    autoresponder**; a ``responses`` key containing newlines will effectively
    never be triggered.

Due to how regular expressions are implemented (at least in Python's `re`
module) it's not feasible to apply a regex to a true stream of text. Matching a
regular expression on the standard output or error of a program thus requires
one of a few strategies, most of which are flawed:

* Wait for the entire program's output to finish, then match once on the entire
  thing. For a feature focused on interactive feedback, this is a non-starter.
* Match on the entire contents of the capture buffer after every successful
  read. This "works", but will submit duplicate responses. Without a
  potentially complex and ambiguity-laden "how many times to expect/respond to
  which patterns" DSL, this approach is also unacceptable.
* Match on one chunk of stream output at a time. This has a serious flaw: what
  happens when the pattern you seek exists in the stream, but is broken up by
  the chunked data?

    * Using the actual read chunk size (which is simply some integer tuned for
      efficiency reasons) will always exhibit some chance of this problem, even
      when set to a large value (and doing so not always feasible, either).
    * Chunking the read buffer in a logical fashion (e.g. line-by-line) isn't
      ideal either, but at least allows us to frame the problem: if your
      pattern can be expressed to always fall within the logical chunk, we can
      guarantee that matching will work 100% of the time.

As you can guess based on the above warning, the default implementation of our
autoresponder (`.Runner.respond`) opts for the final approach: it keeps a
"linewise" buffer, which is flushed each time a newline character is found.
This allows reliably responding to prompts (the typical use case of this
feature) while avoiding the pitfalls of other solutions.

Other solutions based on this one are also possible, but have their own
problems:

* If we cared only about responding to static strings and not regular
  expressions, we could simply "chunk" the stream data by the length of the
  longest key in ``responses`` - if such a chunk didn't match, there's no way
  additional reads could make a match possible.

    * An alternate responder implementation opting for this approach might well
      appear in the future.

* If we cared about multiline regex patterns, we could try keeping a larger,
  multiline buffer - but this runs afoul of the same problem

.. TODO: uhhhh how DO we know when to actually match, if we're keeping a buffer
and have no idea when to execute a match on it, we're gonna match on it
multiple times, aren't we? I think we need a fabric 1 style "buffer that gets
emptied out when matches are found" for each key in the responses dict???
