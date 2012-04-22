import os

from spec import eq_, skip

from invoke import run

from _utils import support


# Yea, it's not really object-oriented, but whatever :)
class CLI(object):
    "Command-line interface"

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
        cmd = "taskname --boolean"
        skip()

    def flag_then_space_then_value(self):
        cmd = "taskname --flag value"
        skip()

    def flag_then_equals_sign_then_value(self):
        cmd = "taskname --flag=value"
        skip()

    def short_boolean_flag(self):
        cmd = "taskname -f"
        skip()

    def short_flag_then_space_then_value(self):
        cmd = "taskname -f value"
        skip()

    def short_flag_then_equals_sign_then_value(self):
        cmd = "taskname -f=value"
        skip()

    def short_flag_with_adjacent_value(self):
        cmd = "taskname -fvalue"
        skip()

    def flag_value_then_task(self):
        cmd = "task1 -f notatask task2"
        skip()

    def flag_value_same_as_task_name(self):
        cmd = "task1 -f mytask mytask"
        skip()

    def three_tasks_with_args(self):
        cmd = "task1 --task1_bool task2 --task2_arg task2_arg_value task3"
        skip()

    def tasks_with_duplicately_named_kwargs(self):
        cmd = "task1 --myarg=value task2 --myarg=othervalue"
        skip()

    def complex_multitask_invocation(self):
        cmd = "-c integration task1 --bool_arg --val_arg=value task2 --val_arg othervalue -b"
        skip()
