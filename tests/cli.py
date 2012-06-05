import os

from spec import eq_, skip, Spec

from invoke import run
from invoke.parser import Parser, Context
from invoke.collection import Collection
from invoke.task import task

from _utils import support


class CLI(Spec):
    "Command-line interface"

    def setup(self):
        @task
        def mytask(mystring, s, boolean=False, b=False):
            pass
        @task
        def mytask2():
            pass
        c = Collection()
        c.add_task('mytask', mytask)
        c.add_task('mytask2', mytask2)
        self.c = c

    def _parser(self):
        return Parser(self.c.to_contexts())

    def _compare(self, invoke, flagname, value):
        invoke = "mytask " + invoke
        result = self._parser().parse_argv(invoke.split())
        eq_(result.to_dict()['mytask'][flagname], value)

    # Yo dogfood, I heard you like invoking
    def basic_invocation(self):
        os.chdir(support)
        result = run("invoke -c integration print_foo")
        eq_(result.stdout, "foo\n")

    def implicit_task_module(self):
        # Contains tasks.py
        os.chdir(support + '/implicit/')
        # Doesn't specify --collection
        result = run("invoke foo")
        eq_(result.stdout, "Hm\n")

    def boolean_args(self):
        self._compare("--boolean", 'boolean', True)

    def flag_then_space_then_value(self):
        self._compare("--mystring foo", 'mystring', 'foo')

    def flag_then_equals_sign_then_value(self):
        self._compare("--mystring=foo", 'mystring', 'foo')

    def short_boolean_flag(self):
        self._compare("-b", 'b', True)

    def short_flag_then_space_then_value(self):
        self._compare("-s value", 's', 'value')

    def short_flag_then_equals_sign_then_value(self):
        self._compare("-s=value", 's', 'value')

    def short_flag_with_adjacent_value(self):
        "taskname -fvalue"
        skip()

    def flag_value_then_task(self):
        r = self._parser().parse_argv("mytask -s value mytask2".split())
        eq_(len(r), 2)
        eq_(r[0].name, 'mytask')
        eq_(r[0].args.s.value, 'value')
        eq_(r[1].name, 'mytask2')

    def flag_value_same_as_task_name(self):
        "task1 -f mytask mytask"
        skip()

    def three_tasks_with_args(self):
        "task1 --task1_bool task2 --task2_arg task2_arg_value task3"
        skip()

    def tasks_with_duplicately_named_kwargs(self):
        "task1 --myarg=value task2 --myarg=othervalue"
        skip()

    def complex_multitask_invocation(self):
        "-c integration task1 --bool_arg --val_arg=value task2 --val_arg othervalue -b"
        skip()

    def multiple_short_flags_adjacent(self):
        "task1 -abc => equiv to task1 -a -b -c"
        skip()
