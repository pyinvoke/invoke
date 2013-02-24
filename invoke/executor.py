class Executor(object):
    def __init__(self, collection):
        self.collection = collection

    def execute(self, name, kwargs=None):
        kwargs = kwargs or {}
        self.collection[name].body(**kwargs)
