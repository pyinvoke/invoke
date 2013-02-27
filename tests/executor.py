from spec import Spec, eq_
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

    def pre_tasks(self):
        task2 = Task(Mock(), pre=['func'])
        # TODO: maybe not use mutation here...
        self.coll.add_task(task2, 'task2')
        self.executor.execute(name='task2')
        eq_(self.coll['func'].body.call_count, 1)
