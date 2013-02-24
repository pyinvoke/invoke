class Executor(object):
    def __init__(self, collection):
        self.collection = collection

    def execute(self, name, kwargs=None):
        kwargs = kwargs or {}
        task = self.collection[name]
        self.execute_pretasks(task)
        task.body(**kwargs)

    def execute_pretasks(self, task):
        for pretask in task.pre:
            self.execute(name=pretask)
