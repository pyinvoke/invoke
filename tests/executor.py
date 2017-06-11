from spec import eq_, ok_
from mock import Mock

from invoke import Collection, Config, Context, Executor, Task, call, task
from invoke.parser import ParserContext

from _util import expect, IntegrationSpec


class Executor_(IntegrationSpec):
    def setup(self):
        s = super(Executor_, self)
        s.setup()
        self.task1 = Task(Mock(return_value=7))
        self.task2 = Task(Mock(return_value=10), pre=[self.task1])
        self.task3 = Task(Mock(), pre=[self.task1])
        self.task4 = Task(Mock(return_value=15), post=[self.task1])
        self.contextualized = Task(Mock())
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

        def can_grant_access_to_core_arg_parse_result(self):
            c = ParserContext()
            ok_(Executor(collection=Collection(), core=c).core is c)

        def core_arg_parse_result_defaults_to_None(self):
            ok_(Executor(collection=Collection()).core is None)

    class execute:
        def base_case(self):
            self.executor.execute('task1')
            assert self.task1.body.called

        def kwargs(self):
            k = {'foo': 'bar'}
            self.executor.execute(('task1', k))
            args = self.task1.body.call_args[0]
            kwargs = self.task1.body.call_args[1]
            ok_(isinstance(args[0], Context))
            eq_(len(args), 1)
            eq_(kwargs['foo'], 'bar')

        def contextualized_tasks_are_given_parser_context_arg(self):
            self.executor.execute('contextualized')
            args = self.contextualized.body.call_args[0]
            eq_(len(args), 1)
            ok_(isinstance(args[0], Context))

        def default_tasks_called_when_no_tasks_specified(self):
            # NOTE: when no tasks AND no default, Program will print global
            # help. We just won't do anything at all, which is fine for now.
            task = Task(Mock('default-task'))
            coll = Collection()
            coll.add_task(task, name='mytask', default=True)
            executor = Executor(collection=coll)
            executor.execute()
            args = task.body.call_args[0]
            ok_(isinstance(args[0], Context))
            eq_(len(args), 1)

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
                args = body.call_args[0]
                eq_(len(args), 1)
                ok_(isinstance(args[0], Context))

        def _call_objs(self):
            # Setup
            pre_body, post_body = Mock(), Mock()
            t1 = Task(pre_body)
            t2 = Task(post_body)
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
            assert isinstance(args[0], Context)
            eq_(args[1], 5)
            # Post-task asserts
            args, kwargs = post_body.call_args
            eq_(kwargs, {'biz': 'baz'})
            assert isinstance(args[0], Context)
            eq_(args[1], 7)

        def call_objs_play_well_with_context_args(self):
            self._call_objs()

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
            param_list = []
            for body_call in body.call_args_list:
                ok_(isinstance(body_call[0][0], Context))
                param_list.append(body_call[0][1])
            ok_(set(param_list) == set((5, 7)))

    class collection_driven_config:
        "Collection-driven config concerns"
        def hands_collection_configuration_to_context(self):
            @task
            def mytask(ctx):
                eq_(ctx.my_key, 'value')
            c = Collection(mytask)
            c.configure({'my_key': 'value'})
            Executor(collection=c).execute('mytask')

        def hands_task_specific_configuration_to_context(self):
            @task
            def mytask(ctx):
                eq_(ctx.my_key, 'value')
            @task
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
            @task(default=True)
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

    class inter_task_context_and_config_sharing:
        def context_is_new_but_config_is_same(self):
            @task
            def task1(c):
                return c
            @task
            def task2(c):
                return c
            coll = Collection(task1, task2)
            ret = Executor(collection=coll).execute('task1', 'task2')
            c1 = ret[task1]
            c2 = ret[task2]
            ok_(c1 is not c2)
            # TODO: eventually we may want to change this again, as long as the
            # effective values within the config are still matching...? Ehh
            ok_(c1.config is c2.config)

        def new_config_data_is_preserved_between_tasks(self):
            @task
            def task1(c):
                c.foo = 'bar'
                # NOTE: returned for test inspection, not as mechanism of
                # sharing data!
                return c
            @task
            def task2(c):
                return c
            coll = Collection(task1, task2)
            ret = Executor(collection=coll).execute('task1', 'task2')
            c2 = ret[task2]
            ok_('foo' in c2.config)
            eq_(c2.foo, 'bar')

        def config_mutation_is_preserved_between_tasks(self):
            @task
            def task1(c):
                c.config.run.echo = True
                # NOTE: returned for test inspection, not as mechanism of
                # sharing data!
                return c
            @task
            def task2(c):
                return c
            coll = Collection(task1, task2)
            ret = Executor(collection=coll).execute('task1', 'task2')
            c2 = ret[task2]
            eq_(c2.config.run.echo, True)

        def config_deletion_is_preserved_between_tasks(self):
            @task
            def task1(c):
                del c.config.run.echo
                # NOTE: returned for test inspection, not as mechanism of
                # sharing data!
                return c
            @task
            def task2(c):
                return c
            coll = Collection(task1, task2)
            ret = Executor(collection=coll).execute('task1', 'task2')
            c2 = ret[task2]
            ok_('echo' not in c2.config.run)
