==============
Task execution
==============

* CLI parsing first-pass occurs, which obtains core settings/flags.
* Global and per-user config files are loaded, pending some of those core
  options.
* A task namespace is loaded up via one or more Collections -- see
  :doc:`concepts/cli/loading`.
    * Somewhere in here, pre/post lists are parsed & any strings replaced with
      the looked-up real task objects (or errors raised).
* The tasks + their options/args are parsed in the second parser pass (within
  context of that root Collection).
* An ExecutionContext object is created and given the Collection and the parse
  result. The rest of this is a method call or calls on the EC object.
* The requested tasks are invoked with the parsed options:
    * Serial mode (default):
        * For each task
            * It's examined for a 'pre' list of tasks. For each of those:
                * If global setting re: run-once is set, check data structure on
                  the EC for that task.
                    * If set, skip to next
                    * If not set, set and execute (recurse)
                * If run-once is not set, execute (recurse)
                    * Possibly incrementing a run counter?
            * Its main body is run with the matched options/args from the CLI.
            * Post tasks are run in the same way as pre tasks were.
            * Return value is stored back into the EC?
    * Parallel mode:
        * What is the parallelism dimension? Callers need some way of
          specifying what is different for each individual run. Presume some
          sort of partial application -- with f(x), execute f for x over [1, 2,
          3]?
            * Can't think of useful CLI API for this, probably limited to use
              of the API within your own 'meta' tasks?
                * Thinking: @parallel(argname=[list, of, values])
                * Except, like Fab, this doesn't necessarily imply
                  parallelization, only multiplication/whatever.
                * py.test does this doesn't it...see how they treat this
            * Sans Fab SSH type stuff, can we even offer any benefit over
              literally using functools.partial?
            * I guess the before/after chain junk -- but what if they don't
              want that?
        * How to handle multiple tasks here?
            * Parallel on task 1, then parallel on task 2 (Fabric 1.x style)?
            * Parallel across all tasks?
                * How does that reconcile w/ the parallel dimension
                  specification? Assu
* Done.
