=========
Prior art
=========

Why another task running Python library? As usual, the short answer is "there
were already great 80-90% solutions out there, but none that fit our needs
100%." Specifically:

* **Multiple tasks at once** - almost no other Python command-line oriented
  libraries allow for invocations like::
  
    runner --core-opts task1 --task1-opts task2 --task2-opts
    
  and the few that do have half-baked implementations of the feature or are
  lacking in other ways.
* **Simplicity** - tools that try to do many things often suffer for it due to
  lack of focus. We wanted to build something clean and simple that just did
  one thing (ok...two things) well.
* **Customizability/control** - Invoke was designed to work well with (and be a
  foundation for) other tools such as `Fabric <http://fabfile.org>`_'s second
  version, and we felt that the work needed to adapt existing tools towards
  this goal would impede progress.

Some of the pre-existing solutions in this space in the Python world include:

* `Argh <http://packages.python.org/argh/index.html>`_: One of the more
  appealing options, but being built on argparse it doesn't support the
  multi-task invocation we needed. Also has its own "prior art" list which is
  worth your time.
* `Baker <http://pypi.python.org/pypi/Baker/1.02>`_: Nice and simple, but
  unfortunately too much so for our needs.
* `Paver <http://paver.github.com/paver/>`_: Tries to do too much, clunky API,
  user-hostile error messages, multi-task feature existed but was lacking.
* `Argparse <http://docs.python.org/library/argparse.html>`_: The modern gold
  standard for CLI parsing (albeit without command execution). Unfortunately,
  we were unable to get multiple tasks working despite lots of experimentation.
  Multiple tasks with their own potentially overlapping argument names, simply
  doesn't mesh with how ``argparse`` thinks about the command line.
