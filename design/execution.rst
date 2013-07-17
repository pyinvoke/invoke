==============
Task execution
==============

* CLI parsing first-pass occurs, which obtains core settings/flags.
* Global and per-user config files are loaded, pending some of those core
  options.
* A task namespace is loaded up via one or more Collections -- see
  :doc:`concepts/loading`.
    * Somewhere in here, pre/post lists are parsed & any strings replaced with
      the looked-up real task objects (or errors raised).
* The tasks + their options/args are parsed in the second parser pass (within
  context of that root Collection).
* An ExecutionContext object is created and given the Collection and the parse
  result. The rest of this is a method call or calls on the EC object.
* The requested tasks are invoked with the parsed options:
    * Specifically, this method call needs to mate each task with some
      "N-times" structure determining how many times to run the task & allowing
      parameterization if desired (basically it's just dispatching to the
      "real" runner as per below)
        * Default is simply to run one time w/ no parameterization, simply
          whatever the CLI provided.
        * Users wanting to parameterize would need to supply a parameterization
          structure describing the parameters themselves & the values, either
          the way py.test's @parametrize does it (args only) or via dicts for
          kwargs.
            * How to square this with CLI values? Given no clean way of
              declaring this on the CLI, maybe leave it lib-only for now?
        * There also needs to be a 'method' of invocation determining how the
          execution proceeds, aka the below serial-vs-parallel stuff. Should be
          overrideable / a class or function that is injected.
            * Also needs to preserve link back to the EC which is the
              statekeeper for runs-once-globally stuff.
            * Any parallelization would take place "inside" this class.
        * How to square pre/post with these different run types?
            * May want to differ depending on algorithm, e.g. whether the
              pre/post's run "with" the task (so if task is run N times, so are
              the pre/posts) or independently (pre/posts run once, task runs N
              times)
            * So probably a parent class with the default behavior we want,
              subclassed for serial/parallel, open to user extension.
            * Default behavior for pre/post should be what? What's least
              surprising? MOST of the time any N!=1 runs would likely not be
              making use of pre/post, but must handle it anyways.
                * Basically it comes down to "run pre/post once" vs "run
                  pre/post with task". Which is worse to accidentally do to the
                  other?
                    * If user expected pre/post to run once and task to run N
                      times, and pre/post run N times instead, stuff might get
                      cleaned/compiled/uploaded/etc too many times.
                    * If user expected pre/post to run N times and task to run
                      N times, and pre/post run once instead, task might see
                      state bleed or only one "result" instead of N, etc.
                    * Feels like the "default to run pre/post's once regardless
                      of how many times task runs" is somewhat less likely to
                      have bad results.
                    * However, "run pre/posts 'with' the task N times" feels
                      like it might be the more intuitive/unsurprising
                      behavior? Poll folks.
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
        * How to handle multiple tasks here?
            * Parallel on task 1, then parallel on task 2 (Fabric 1.x style)?
            * Parallel across all tasks (aka task 1 + task 2 for param 1, then
              task 2 + task 2 for param 2, etc)
                * How does that reconcile w/ the parallel dimension
                  specification, given that's usually per-task (aka
                  "parameterize over arg 'foo' with values a,b,c" => that only
                  works with the task that has arg 'foo')
* Done.

More pre/post run crap:

* What does "runs once" really mean? Does it just mean that a given task's call
  chain, when expanded, shouldn't run any task >1 time? Or does this extend
  across the entire run of N tasks?
    * E.g. that 1st case is: 'invoke foo', foo has prereq on bar and biz, bar
      also has prereq on biz. "runs once" means biz only gets run one time, and
      this is easy to do because once we expand everything out we can dedupe.
    * 2nd case is 'invoke foo bar', foo has prereq on (why not) bar. How many
      times does bar run? What if foo and bar both had prereqs on biz (but foo
      no longer depends on bar) -- should biz run 2x here or 1x?
