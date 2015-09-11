from spec import eq_, ok_
from mock import Mock, call as mock_call

from invoke.collection import Collection
from invoke.config import Config
from invoke.context import Context
from invoke.executor import Executor
from invoke.tasks import Task, ctask, call

from _utils import expect, IntegrationSpec


class Executor_(IntegrationSpec):
    def setup(self):
        s = super(Executor_, self)
        s.setup()
        self.task1 = Task(Mock(return_value=7))
        self.task2 = Task(Mock(return_value=10), pre=[self.task1])
        self.task3 = Task(Mock(), pre=[self.task1])
        self.task4 = Task(Mock(return_value=15), post=[self.task1])
        self.contextualized = Task(Mock(), contextualized=True)
        coll = Collection()
        coll.add_task(self.task1, name='task1')
        coll.add_task(self.task2, name='task2')
        coll.add_task(self.task3, name='task3')
        coll.add_task(self.task4, name='task4')
        coll.add_task(self.contextualized, name='contextualized')
        self.executor = Executor(collection=coll)

    class init:
        "__init__"
        def allows_collection_and_config(self):
            coll = Collection()
            conf = Config()
            e = Executor(collection=coll, config=conf)
            assert e.collection is coll
            assert e.config is conf

        def uses_blank_config_by_default(self):
            e = Executor(collection=Collection())
            assert isinstance(e.config, Config)

    class execute:
        def base_case(self):
            self.executor.execute('task1')
            assert self.task1.body.called

        def kwargs(self):
            k = {'foo': 'bar'}
            self.executor.execute(('task1', k))
            self.task1.body.assert_called_once_with(**k)

        def contextualized_tasks_are_given_parser_context_arg(self):
            self.executor.execute('contextualized')
            args = self.contextualized.body.call_args[0]
            eq_(len(args), 1)
            ok_(isinstance(args[0], Context))

    class basic_pre_post:
        "basic pre/post task functionality"

        def pre_tasks(self):
            self.executor.execute('task2')
            eq_(self.task1.body.call_count, 1)

        def post_tasks(self):
            self.executor.execute('task4')
            eq_(self.task1.body.call_count, 1)

        def calls_default_to_empty_args_always(self):
            pre_body, post_body = Mock(), Mock()
            t1 = Task(pre_body)
            t2 = Task(post_body)
            t3 = Task(Mock(), pre=[t1], post=[t2])
            e = Executor(collection=Collection(t1=t1, t2=t2, t3=t3))
            e.execute(('t3', {'something': 'meh'}))
            for body in (pre_body, post_body):
                eq_(body.call_args, tuple())

        def _call_objs(self, contextualized):
            # Setup
            pre_body, post_body = Mock(), Mock()
            t1 = Task(pre_body, contextualized=contextualized)
            t2 = Task(post_body, contextualized=contextualized)
            t3 = Task(Mock(),
                pre=[call(t1, 5, foo='bar')],
                post=[call(t2, 7, biz='baz')],
            )
            c = Collection(t1=t1, t2=t2, t3=t3)
            e = Executor(collection=c)
            e.execute('t3')
            # Pre-task asserts
            args, kwargs = pre_body.call_args
            eq_(kwargs, {'foo': 'bar'})
            if contextualized:
                assert isinstance(args[0], Context)
                eq_(args[1], 5)
            else:
                eq_(args, (5,))
            # Post-task asserts
            args, kwargs = post_body.call_args
            eq_(kwargs, {'biz': 'baz'})
            if contextualized:
                assert isinstance(args[0], Context)
                eq_(args[1], 7)
            else:
                eq_(args, (7,))

        def may_be_call_objects_specifying_args(self):
            self._call_objs(False)

        def call_objs_play_well_with_context_args(self):
            self._call_objs(True)

    class deduping_and_chaining:
        def chaining_is_depth_first(self):
            expect('-c depth_first deploy', out="""
Cleaning HTML
Cleaning .tar.gz files
Cleaned everything
Making directories
Building
Deploying
Preparing for testing
Testing
""".lstrip())

        def _expect(self, args, expected):
            expect('-c integration {0}'.format(args), out=expected.lstrip())

        class adjacent_hooks:
            def deduping(self):
                self._expect('biz', """
foo
bar
biz
post1
post2
""")

            def no_deduping(self):
                self._expect('--no-dedupe biz', """
foo
foo
bar
biz
post1
post2
post2
""")

        class non_adjacent_hooks:
            def deduping(self):
                self._expect('boz', """
foo
bar
boz
post2
post1
""")

            def no_deduping(self):
                self._expect('--no-dedupe boz', """
foo
bar
foo
boz
post2
post1
post2
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
            e = Executor(collection=c)
            e.execute('t2')
            # Does not call the second t1(5)
            body.assert_has_calls([mock_call(5), mock_call(7)])

    class collection_driven_config:
        "Collection-driven config concerns"
        def hands_collection_configuration_to_context(self):
            @ctask
            def mytask(ctx):
                eq_(ctx.my_key, 'value')
            c = Collection(mytask)
            c.configure({'my_key': 'value'})
            Executor(collection=c).execute('mytask')

        def hands_task_specific_configuration_to_context(self):
            @ctask
            def mytask(ctx):
                eq_(ctx.my_key, 'value')
            @ctask
            def othertask(ctx):
                eq_(ctx.my_key, 'othervalue')
            inner1 = Collection('inner1', mytask)
            inner1.configure({'my_key': 'value'})
            inner2 = Collection('inner2', othertask)
            inner2.configure({'my_key': 'othervalue'})
            c = Collection(inner1, inner2)
            e = Executor(collection=c)
            e.execute('inner1.mytask', 'inner2.othertask')

        def subcollection_config_works_with_default_tasks(self):
            @ctask(default=True)
            def mytask(ctx):
                eq_(ctx.my_key, 'value')
            # Sets up a task "known as" sub.mytask which may be called as
            # just 'sub' due to being default.
            sub = Collection('sub', mytask=mytask)
            sub.configure({'my_key': 'value'})
            main = Collection(sub=sub)
            # Execute via collection default 'task' name.
            Executor(collection=main).execute('sub')

    class returns_return_value_of_specified_task:
        def base_case(self):
            eq_(self.executor.execute('task1'), {self.task1: 7})

        def with_pre_tasks(self):
            eq_(
                self.executor.execute('task2'),
                {self.task1: 7, self.task2: 10}
            )

        def with_post_tasks(self):
            eq_(
                self.executor.execute('task4'),
                {self.task1: 7, self.task4: 15}
            )

    class autoprinting:
        def defaults_to_off_and_no_output(self):
            expect("-c autoprint nope", out="")

        def prints_return_value_to_stdout_when_on(self):
            expect("-c autoprint yup", out="It's alive!\n")

        def prints_return_value_to_stdout_when_on_and_in_collection(self):
            expect("-c autoprint sub.yup", out="It's alive!\n")

        def does_not_fire_on_pre_tasks(self):
            expect("-c autoprint pre_check", out="")

        def does_not_fire_on_post_tasks(self):
            expect("-c autoprint post_check", out="")
