.. _concepts-context:

===========================
State handling: the context
===========================

A common problem task runners face is transmission or storage of values which
are "global" for the current session - values loaded from :doc:`configuration
files <configuration>` (or :ref:`other configuration vectors
<collection-configuration>`), CLI flags, values set by 'setup' tasks, etc.

Some Python libraries (such as `Fabric <http://fabfile.org>`_ 1.x) implement
this via global module state. That approach works in the base case but makes
testing difficult and error prone, limits concurrency, and makes the software
more complex to use and extend.

Invoke encapsulates its state in an explicit `~.Context` object, handed to
tasks when they execute or instantiated and used by hand. The context is the
primary API endpoint, offering methods which honor the current state (such as
`.Context.run`) as well as access to that state itself.
