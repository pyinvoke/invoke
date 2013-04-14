from spec import Spec, eq_, skip
from mock import Mock

from invoke.executor import Executor
from invoke.collection import Collection
from invoke.tasks import Task


class Executor_(Spec):
    def setup(self):
        self.task1 = Task(Mock(return_value=7))
        self.task2 = Task(Mock(return_value=10), pre=['task1'])
        self.task3 = Task(Mock(), pre=['task1'])
        coll = Collection()
        coll.add_task(self.task1, name='task1')
        coll.add_task(self.task2, name='task2')
        coll.add_task(self.task3, name='task3')
        self.executor = Executor(coll)
        self.coll = coll

    def base_case(self):
        self.executor.execute('task1')
        assert self.task1.body.called

    def kwargs(self):
        k = {'foo': 'bar'}
        self.executor.execute(name='task1', kwargs=k)
        self.task1.body.assert_called_once_with(**k)

    def pre_tasks(self):
        self.executor.execute(name='task2')
        eq_(self.task1.body.call_count, 1)

    def enabled_deduping(self):
        self.executor.execute(name='task2')
        self.executor.execute(name='task3')
        eq_(self.task1.body.call_count, 1)

    def disabled_deduping(self):
        self.executor.execute(name='task2', dedupe=False)
        self.executor.execute(name='task3', dedupe=False)
        eq_(self.task1.body.call_count, 2)

    class returns_return_value_of_specified_task:
        def base_case(self):
            eq_(self.parent.executor.execute(name='task1'), 7)

        def with_pre_tasks(self):
            eq_(self.parent.executor.execute(name='task2'), 10)

        def with_post_tasks(self):
            skip()
