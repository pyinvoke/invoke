from mock import Mock
import pytest

from invoke import Collection, Config, Context, Executor, Task, call, task
from invoke.parser import ParserContext, ParseResult

from _util import expect


# TODO: why does this not work as a decorator? probably relaxed's fault - but
# how?
pytestmark = pytest.mark.usefixtures("integration")


class Executor_:
    def setup(self):
        self.task1 = Task(Mock(return_value=7))
        # TODO: replace below w/ modern call graph arg names?
        self.task2 = Task(Mock(return_value=10), pre=[self.task1])
        self.task3 = Task(Mock(), pre=[self.task1])
        self.task4 = Task(Mock(return_value=15), post=[self.task1])
        self.contextualized = Task(Mock())
        coll = Collection()
        coll.add_task(self.task1, name="task1")
        coll.add_task(self.task2, name="task2")
        coll.add_task(self.task3, name="task3")
        coll.add_task(self.task4, name="task4")
        coll.add_task(self.contextualized, name="contextualized")
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
            c = ParseResult([ParserContext(name="mytask")])
            e = Executor(collection=Collection(), core=c)
            assert e.core is c
            # Sanity test of real-world access/usage
            assert len(e.core) == 1
            assert e.core[0].name == "mytask"
            assert len(e.core[0].args) == 0

        def core_arg_parse_result_defaults_to_None(self):
            assert Executor(collection=Collection()).core is None

    class execute:
        def base_case(self):
            self.executor.execute("task1")
            assert self.task1.body.called

        def kwargs(self):
            k = {"foo": "bar"}
            self.executor.execute(("task1", k))
            args = self.task1.body.call_args[0]
            kwargs = self.task1.body.call_args[1]
            assert isinstance(args[0], Context)
            assert len(args) == 1
            assert kwargs["foo"] == "bar"

        def contextualized_tasks_are_given_parser_context_arg(self):
            self.executor.execute("contextualized")
            args = self.contextualized.body.call_args[0]
            assert len(args) == 1
            assert isinstance(args[0], Context)

        def default_tasks_called_when_no_tasks_specified(self):
            # NOTE: when no tasks AND no default, Program will print global
            # help. We just won't do anything at all, which is fine for now.
            task = Task(Mock("default-task"))
            coll = Collection()
            coll.add_task(task, name="mytask", default=True)
            executor = Executor(collection=coll)
            executor.execute()
            args = task.body.call_args[0]
            assert isinstance(args[0], Context)
            assert len(args) == 1

    # TODO: merge with call graph tests below such that pre/post get worked
    # into new system.
    class old_pre_post:
        "old pre/post task functionality"

        def pre_tasks(self):
            self.executor.execute("task2")
            assert self.task1.body.call_count == 1

        def post_tasks(self):
            self.executor.execute("task4")
            assert self.task1.body.call_count == 1

        def calls_default_to_empty_args_always(self):
            pre_body, post_body = Mock(), Mock()
            t1 = Task(pre_body)
            t2 = Task(post_body)
            t3 = Task(Mock(), pre=[t1], post=[t2])
            e = Executor(collection=Collection(t1=t1, t2=t2, t3=t3))
            e.execute(("t3", {"something": "meh"}))
            for body in (pre_body, post_body):
                args = body.call_args[0]
                assert len(args) == 1
                assert isinstance(args[0], Context)

        def _call_objs(self):
            # Setup
            pre_body, post_body = Mock(), Mock()
            t1 = Task(pre_body)
            t2 = Task(post_body)
            t3 = Task(
                Mock(),
                pre=[call(t1, 5, foo="bar")],
                post=[call(t2, 7, biz="baz")],
            )
            c = Collection(t1=t1, t2=t2, t3=t3)
            e = Executor(collection=c)
            e.execute("t3")
            # Pre-task asserts
            args, kwargs = pre_body.call_args
            assert kwargs == {"foo": "bar"}
            assert isinstance(args[0], Context)
            assert args[1] == 5
            # Post-task asserts
            args, kwargs = post_body.call_args
            assert kwargs == {"biz": "baz"}
            assert isinstance(args[0], Context)
            assert args[1] == 7

        def call_objs_play_well_with_context_args(self):
            self._call_objs()

    # TODO: ditto
    class deduping_and_chaining:
        def chaining_is_depth_first(self):
            expect(
                "-c depth_first deploy",
                out="""
Cleaning HTML
Cleaning .tar.gz files
Cleaned everything
Making directories
Building
Deploying
Preparing for testing
Testing
""".lstrip(),
            )

        def _expect(self, args, expected):
            expect("-c integration {}".format(args), out=expected.lstrip())

        class adjacent_hooks:
            def deduping(self):
                self._expect(
                    "biz",
                    """
foo
bar
biz
post1
post2
""",
                )

            def no_deduping(self):
                self._expect(
                    "--no-dedupe biz",
                    """
foo
foo
bar
biz
post1
post2
post2
""",
                )

        class non_adjacent_hooks:
            def deduping(self):
                self._expect(
                    "boz",
                    """
foo
bar
boz
post2
post1
""",
                )

            def no_deduping(self):
                self._expect(
                    "--no-dedupe boz",
                    """
foo
bar
foo
boz
post2
post1
post2
""",
                )

        # AKA, a (foo) (foo -> bar) scenario arising from foo + bar
        class adjacent_top_level_tasks:
            def deduping(self):
                self._expect(
                    "foo bar",
                    """
foo
bar
""",
                )

            def no_deduping(self):
                self._expect(
                    "--no-dedupe foo bar",
                    """
foo
foo
bar
""",
                )

        # AKA (foo -> bar) (foo)
        class non_adjacent_top_level_tasks:
            def deduping(self):
                self._expect(
                    "foo bar",
                    """
foo
bar
""",
                )

            def no_deduping(self):
                self._expect(
                    "--no-dedupe foo bar",
                    """
foo
foo
bar
""",
                )

        def deduping_treats_different_calls_to_same_task_differently(self):
            body = Mock()
            t1 = Task(body)
            pre = [call(t1, 5), call(t1, 7), call(t1, 5)]
            t2 = Task(Mock(), pre=pre)
            c = Collection(t1=t1, t2=t2)
            e = Executor(collection=c)
            e.execute("t2")
            # Does not call the second t1(5)
            param_list = []
            for body_call in body.call_args_list:
                assert isinstance(body_call[0][0], Context)
                param_list.append(body_call[0][1])
            assert set(param_list) == {5, 7}

    class call_graph:
        def basic_dependencies(self):
            self.executor.execute("task2")
            assert self.task1.body.call_count == 1

        def basic_followups(self):
            self.executor.execute("task4")
            assert self.task1.body.call_count == 1

        # TODO: this needs to change for #261...somehow...
        def calls_default_to_empty_args_always(self):
            dep_body, followup_body = Mock(), Mock()
            t1 = Task(dep_body)
            t2 = Task(followup_body)
            t3 = Task(Mock(), depends_on=[t1], afterwards=[t2])
            e = Executor(collection=Collection(t1=t1, t2=t2, t3=t3))
            e.execute(("t3", {"something": "meh"}))
            for body in (dep_body, followup_body):
                args = body.call_args[0]
                assert len(args) == 1
                assert isinstance(args[0], Context)

        def call_objs_play_well_with_context_args(self):
            # Setup
            dep_body, followup_body = Mock(), Mock()
            t1 = Task(dep_body)
            t2 = Task(followup_body)
            t3 = Task(
                Mock(),
                depends_on=[call(t1, 5, foo="bar")],
                afterwards=[call(t2, 7, biz="baz")],
            )
            c = Collection(t1=t1, t2=t2, t3=t3)
            e = Executor(collection=c)
            e.execute("t3")
            # Dependency asserts
            args, kwargs = dep_body.call_args
            assert kwargs == {"foo": "bar"}
            assert isinstance(args[0], Context)
            assert args[1] == 5
            # Followup asserts
            args, kwargs = followup_body.call_args
            assert kwargs == {"biz": "baz"}
            assert isinstance(args[0], Context)
            assert args[1] == 7

        # TODO: this should "mostly" work, with the property that things like
        # "clean -> [clean_html, clean_tgz]" actually means one could
        # parallelize the two sub-clean tasks. For now, we can at least iterate
        # them in the given order, as we did before...?
        def chaining_is_depth_first(self):
            expect(
                "-c depth_first deploy",
                out="""
Cleaning HTML
Cleaning .tar.gz files
Cleaned everything
Making directories
Building
Deploying
Preparing for testing
Testing
""".lstrip(),
            )

        def _expect(self, args, expected):
            expect("-c integration {0}".format(args), out=expected.lstrip())

        def basic_dep_and_followup_collapsing_via_graph(self):
            # TODO: prove that depending on foo+bar, when bar also depends on
            # foo; and following-up with followup1+2, when followup1 follows up
            # with followup2; all of those together (calling biz) does NOT run
            # foo twice, NOR does it run followup2 twice.
            pass

        def cli_tasks_plus_deps_deduplicate(self):
            # bar depends on foo; calling "foo bar" does not run "foo" 2x
            self._expect(
                "foo bar",
                """
foo
bar
""",
            )

        def cli_tasks_plus_followups_deduplicate(self):
            # TODO: same as previous but with a followup instead
            pass

        def dependencies_given_as_cli_tasks_afterwards(self):
            # bar depends on foo; calling "bar foo" DOES run 'foo' twice, i.e.,
            # "foo bar foo".
            # TODO: this
            pass

        def multiple_cli_tasks_with_same_followup(self):
            # Add another task that depends on 'followup2'; run it + followup1
            # (which also depends on followup2); assert that we get "newtask
            # followup1 followup2" and _not_ e.g. "newtask followup2 followup1
            # followup2" _or" "newtask followup2 followup1".
            # TODO: fucking rename all of these to be more realistic? UGH
            # NOTE: this is/was #298
            pass

        # TODO: does this still make sense in a DAG world? think so? or does
        # fixing #261 imply doing away with using calls explicitly? (surely it
        # doesn't, otherwise how do we handle parameterization aka #228)
        # TODO: should we update the concept doc with a few examples of using
        # `call` objects (assuming we do still use em)?
        def graph_treats_different_calls_to_same_task_differently(self):
            body = Mock()
            t1 = Task(body)
            dep = [call(t1, 5), call(t1, 7), call(t1, 5)]
            t2 = Task(Mock(), depends_on=dep)
            c = Collection(t1=t1, t2=t2)
            e = Executor(collection=c)
            e.execute("t2")
            # Does not call the second t1(5)
            param_list = []
            for body_call in body.call_args_list:
                assert isinstance(body_call[0][0], Context)
                param_list.append(body_call[0][1])
            assert set(param_list) == set((5, 7))

    class checks:
        pass
        # TODO: tests for the brand new checks stuff, however that wants to
        # work. Probably basics only...
        # TODO: then add a new test module for the individual checks
        # themselves.

    class collection_driven_config:
        "Collection-driven config concerns"

        def hands_collection_configuration_to_context(self):
            @task
            def mytask(c):
                assert c.my_key == "value"

            c = Collection(mytask)
            c.configure({"my_key": "value"})
            Executor(collection=c).execute("mytask")

        def hands_task_specific_configuration_to_context(self):
            @task
            def mytask(c):
                assert c.my_key == "value"

            @task
            def othertask(c):
                assert c.my_key == "othervalue"

            inner1 = Collection("inner1", mytask)
            inner1.configure({"my_key": "value"})
            inner2 = Collection("inner2", othertask)
            inner2.configure({"my_key": "othervalue"})
            c = Collection(inner1, inner2)
            e = Executor(collection=c)
            e.execute("inner1.mytask", "inner2.othertask")

        def subcollection_config_works_with_default_tasks(self):
            @task(default=True)
            def mytask(c):
                assert c.my_key == "value"

            # Sets up a task "known as" sub.mytask which may be called as
            # just 'sub' due to being default.
            sub = Collection("sub", mytask=mytask)
            sub.configure({"my_key": "value"})
            main = Collection(sub=sub)
            # Execute via collection default 'task' name.
            Executor(collection=main).execute("sub")

    class returns_return_value_of_specified_task:
        def base_case(self):
            assert self.executor.execute("task1") == {self.task1: 7}

        # TODO: turn these into regular call graph args, or add duplicate-ish
        # tests?
        def with_pre_tasks(self):
            result = self.executor.execute("task2")
            assert result == {self.task1: 7, self.task2: 10}

        def with_post_tasks(self):
            result = self.executor.execute("task4")
            assert result == {self.task1: 7, self.task4: 15}

    class autoprinting:
        def defaults_to_off_and_no_output(self):
            expect("-c autoprint nope", out="")

        def prints_return_value_to_stdout_when_on(self):
            expect("-c autoprint yup", out="It's alive!\n")

        def prints_return_value_to_stdout_when_on_and_in_collection(self):
            expect("-c autoprint sub.yup", out="It's alive!\n")

        # TODO: ditto, do we keep these and add new for new args, or no?
        def does_not_fire_on_pre_tasks(self):
            expect("-c autoprint pre-check", out="")

        def does_not_fire_on_post_tasks(self):
            expect("-c autoprint post-check", out="")

    class inter_task_context_and_config_sharing:
        def context_is_new_but_config_is_same(self):
            @task
            def task1(c):
                return c

            @task
            def task2(c):
                return c

            coll = Collection(task1, task2)
            ret = Executor(collection=coll).execute("task1", "task2")
            c1 = ret[task1]
            c2 = ret[task2]
            assert c1 is not c2
            # TODO: eventually we may want to change this again, as long as the
            # effective values within the config are still matching...? Ehh
            assert c1.config is c2.config

        def new_config_data_is_preserved_between_tasks(self):
            @task
            def task1(c):
                c.foo = "bar"
                # NOTE: returned for test inspection, not as mechanism of
                # sharing data!
                return c

            @task
            def task2(c):
                return c

            coll = Collection(task1, task2)
            ret = Executor(collection=coll).execute("task1", "task2")
            c2 = ret[task2]
            assert "foo" in c2.config
            assert c2.foo == "bar"

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
            ret = Executor(collection=coll).execute("task1", "task2")
            c2 = ret[task2]
            assert c2.config.run.echo is True

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
            ret = Executor(collection=coll).execute("task1", "task2")
            c2 = ret[task2]
            assert "echo" not in c2.config.run
