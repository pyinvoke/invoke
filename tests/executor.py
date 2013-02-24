from spec import Spec
from mock import Mock

from invoke.executor import Executor
from invoke.collection import Collection
from invoke.tasks import Task


class Executor_(Spec):
    def setup(self):
        task = Task(Mock())
        coll = Collection()
        coll.add_task(task, name='func')
        self.executor = Executor(coll)
        self.task = task
        self.coll = coll

    def base_case(self):
        self.executor.execute('func')
        assert self.task.body.called

    def kwargs(self):
        k = {'foo': 'bar'}
        self.executor.execute(name='func', kwargs=k)
        self.task.body.assert_called_once_with(**k)
