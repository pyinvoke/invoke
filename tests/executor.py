from spec import Spec, eq_, skip, trap
from mock import Mock, call as mock_call

from invoke.context import Context
from invoke.executor import Executor
from invoke.collection import Collection
from invoke.tasks import Task, ctask, call

from _utils import _output_eq, IntegrationSpec


class Executor_(IntegrationSpec):
    def setup(self):
        s = super(Executor_, self)
        s.setup()
        self.task1 = Task(Mock(return_value=7))
        self.task2 = Task(Mock(return_value=10), pre=[self.task1])
        self.task3 = Task(Mock(), pre=[self.task1])
        coll = Collection()
        coll.add_task(self.task1, name='task1')
        coll.add_task(self.task2, name='task2')
        coll.add_task(self.task3, name='task3')
        self.executor = Executor(collection=coll, context=Context())

    class init:
        "__init__"
        def allows_collection_and_context(self):
            coll = Collection()
            cont = Context()
            e = Executor(collection=coll, context=cont)
            assert e.collection is coll
            assert e.context is cont

        def uses_blank_context_by_default(self):
            e = Executor(collection=Collection())
            assert isinstance(e.context, Context)

    class execute:
        def base_case(self):
            self.executor.execute('task1')
            assert self.task1.body.called

        def kwargs(self):
            k = {'foo': 'bar'}
            self.executor.execute(('task1', k))
            self.task1.body.assert_called_once_with(**k)

        def pre_tasks(self):
            self.executor.execute('task2')
            eq_(self.task1.body.call_count, 1)

        def pre_task_calls_default_to_empty_args_regardless_of_main_args(self):
            body = Mock()
            t1 = Task(body)
            t2 = Task(Mock(), pre=[t1])
            e = Executor(
                collection=Collection(t1=t1, t2=t2),
                context=Context()
            )
            e.execute(('t2', {'something': 'meh'}))
            eq_(body.call_args, tuple())

        def _call_objs(self, contextualized):
            body = Mock()
            t1 = Task(body, contextualized=contextualized)
            t2 = Task(Mock(), pre=[call(t1, 5, foo='bar')])
            c = Collection(t1=t1, t2=t2)
            e = Executor(collection=c, context=Context())
            e.execute('t2')
            args, kwargs = body.call_args
            eq_(kwargs, {'foo': 'bar'})
            if contextualized:
                assert isinstance(args[0], Context)
                eq_(args[1], 5)
            else:
                eq_(args, (5,))

        def pre_tasks_may_be_call_objects_specifying_args(self):
            self._call_objs(False)

        def call_obj_pre_tasks_play_well_with_context_args(self):
            self._call_objs(True)

    class deduping_and_chaining:
        def chaining_is_depth_first(self):
            _output_eq('-c depth_first deploy', """
Cleaning HTML
Cleaning .tar.gz files
Cleaned everything
Making directories
Building
Deploying
""".lstrip())

        def _expect(self, args, expected):
            _output_eq('-c integration {0}'.format(args), expected.lstrip())

        class adjacent_pretask:
            def deduping(self):
                self._expect('biz', """
foo
bar
biz
""")

            def no_deduping(self):
                self._expect('--no-dedupe biz', """
foo
foo
bar
biz
""")

        class non_adjacent_pretask:
            def deduping(self):
                self._expect('boz', """
foo
bar
boz
""")

            def no_deduping(self):
                self._expect('--no-dedupe boz', """
foo
bar
foo
boz
""")

        # AKA, a (foo) (foo -> bar) scenario arising from foo + bar
        class adjacent_top_level_tasks:
            def deduping(self):
                self._expect('foo bar', """
foo
bar
""")

            def no_deduping(self):
                self._expect('--no-dedupe foo bar', """
foo
foo
bar
""")

        # AKA (foo -> bar) (foo)
        class non_adjacent_top_level_tasks:
            def deduping(self):
                self._expect('foo bar', """
foo
bar
""")

            def no_deduping(self):
                self._expect('--no-dedupe foo bar', """
foo
foo
bar
""")


        def deduping_treats_different_calls_to_same_task_differently(self):
            body = Mock()
            t1 = Task(body)
            pre = [call(t1, 5), call(t1, 7), call(t1, 5)]
            t2 = Task(Mock(), pre=pre)
            c = Collection(t1=t1, t2=t2)
            e = Executor(collection=c, context=Context())
            e.execute('t2')
            # Does not call the second t1(5)
            body.assert_has_calls([mock_call(5), mock_call(7)])

    class configuration:
        def hands_collection_configuration_to_context(self):
            @ctask
            def mytask(ctx):
                eq_(ctx['my.config.key'], 'value')
            c = Collection(mytask)
            c.configure({'my.config.key': 'value'})
            Executor(collection=c, context=Context()).execute('mytask')

        def hands_task_specific_configuration_to_context(self):
            @ctask
            def mytask(ctx):
                eq_(ctx['my.config.key'], 'value')
            @ctask
            def othertask(ctx):
                eq_(ctx['my.config.key'], 'othervalue')
            inner1 = Collection('inner1', mytask)
            inner1.configure({'my.config.key': 'value'})
            inner2 = Collection('inner2', othertask)
            inner2.configure({'my.config.key': 'othervalue'})
            c = Collection(inner1, inner2)
            e = Executor(collection=c, context=Context())
            e.execute('inner1.mytask')
            e.execute('inner2.othertask')

        def subcollection_config_works_with_default_tasks(self):
            @ctask(default=True)
            def mytask(ctx):
                eq_(ctx['my.config.key'], 'value')
            # Sets up a task "known as" sub.mytask which may be called as just
            # 'sub' due to being default.
            sub = Collection('sub', mytask=mytask)
            sub.configure({'my.config.key': 'value'})
            main = Collection(sub=sub)
            # Execute via collection default 'task' name.
            Executor(collection=main, context=Context()).execute('sub')


    class returns_return_value_of_specified_task:
        def base_case(self):
            eq_(self.executor.execute('task1'), {self.task1: 7})

        def with_pre_tasks(self):
            eq_(
                self.executor.execute('task2'),
                {self.task1: 7, self.task2: 10}
            )

        def with_post_tasks(self):
            skip()
