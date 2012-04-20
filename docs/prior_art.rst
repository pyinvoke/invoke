=========
Prior art
=========

Why another task running Python library? Good question. As usual, the short
answer is "there were already great 80-90% solutions out there, but none that
fit our needs 100%." Specifically:

* **Multiple tasks at once** - almost no other Python command-line oriented
  libraries allow for invocations like::
  
    runner --core-opts task1 --task1-opts task2 --task2-opts
    
  and the few that do have half-backed implementations of the feature or are
  lacking in other ways.
* **Simplicity** - tools that try to do many things often suffer for it due to
  lack of focus. We wanted to build something clean and simple that just did
  one thing well.
* **Customizability/control** - Invoke was designed to work well with other
  tools such as `Fabric <http://fabfile.org>`_ and we felt that the work needed
  to adapt existing tools towards this goal would probably impede progress.

Below are some links and brief notes to alternative tools.

* `Argh <http://packages.python.org/argh/index.html>`_: probably one of the
  neatest looking options, but being built on argparse it doesn't support the
  multi-task invocation we needed. Also has its own "prior art" list which is
  worth your time.
* `Baker <http://pypi.python.org/pypi/Baker/1.02>`_: Nicely simple, but
  unfortunately too much so for our needs.
* `Paver <http://paver.github.com/paver/>`_: Tries to do too much, clunky API,
  user-hostile error messages, multi-task feature existed but was lacking.
* `argparse <http://docs.python.org/library/argparse.html>`_: pretty much the
  modern gold standard for CLI parsing (no command execution, of course) but we
  were unable to get multiple tasks working despite lots of effort. It simply
  doesn't mesh with how ``argparse`` thinks about the command line.
