class Task(object):
    def __init__(self, body, aliases=()):
        self.body = body
        self.aliases = aliases


def task(*args, **kwargs):
    """
    Marks wrapped callable object as a valid Invoke task.

    May be called without any parentheses if no extra options need to be
    specified. Otherwise, the following options are allowed in the parenthese'd
    form:

    * ``aliases``: Specify one or more aliases for this task, allowing it to be
      invoked as multiple different names. For example, a task named ``mytask``
      with a simple ``@task`` wrapper may only be invoked as ``"mytask"``.
      Changing the decorator to be ``@task(aliases=['myothertask'])`` allows
      invocation as ``"mytask"`` *or* ``"myothertask"``.
    """
    # @task -- no options
    if len(args) == 1:
        obj = args[0]
        obj = Task(obj)
        return obj
    # @task(options)
    def inner(obj):
        obj = Task(obj, aliases=kwargs.get('aliases', ()))
        return obj
    return inner
