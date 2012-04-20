==============
CLI invocation
==============

Invoke's command line invocation utilizes traditional style command-line flags
and task name arguments. Some examples before we dive into the dry details:

* Empty invocation: ``invoke``. This will print out help information.
* Explicit help: ``invoke -h``, ``invoke --help``. Same as above.
* Listing available tasks: ``invoke --list``. Prints out a task list but takes
  no other action.
* Other "core" options: ``invoke -c mytasks -c myothertasks --list``. Alters or
  parameterizes core behavior, in this case loading non-default task
  collections, which alters what gets listed.
* Basic task invocation: ``invoke mytaskname``. Just calls any top level task
  named ``mytaskname``.
* Task arguments: ``invoke build --format=html``, ``invoke build --format
  html``, ``invoke build -f pdf``.  Calls ``build`` with its ``format``
  argument set to the value ``"html"``.  Note that arguments may have
  alternative shorthand, and that the equals sign is optional in the longhand
  format (but is not allowed at all in the shorthand.)
* Task boolean arguments (flags): ``invoke build --clean --browse``. Calls
  ``build`` with its ``clean`` and ``browse`` arguments set to ``True``.
* Mixing core and task options/arguments, no overlap: ``invoke -c buildtasks
  build --format=html``.

Open questions
==============

* Should users be allowed to repurpose "core" flags for use as task arguments,
  or should e.g. ``-c``/``--collection`` become "reserved"?
  * Allowing re-use requires 100% strict ordering (core options **must** come
    before any tasks/task options) vs a more GNU style "you can put core
    options anywhere".
  * But if we don't allow reuse then users have to pay attention to a list of
    things they can't use, which is especially problematic for the shorthand
    options like ``-c``.
