import os
import sys
import StringIO

from spec import eq_, skip, Spec, ok_, trap

from invoke.run import run
from invoke.parser import Parser, Context
from invoke.collection import Collection
from invoke.task import task
from invoke.exceptions import Failure

from _utils import support


def _output_eq(cmd, expected):
    return eq_(run(cmd).stdout, expected)


class CLI(Spec):
    "Command-line behavior"
    def setup(self):
        os.chdir(support)

    # Yo dogfood, I heard you like invoking
    @trap
    def basic_invocation(self):
        _output_eq("invoke -c integration print_foo", "foo\n")

    @trap
    def implicit_task_module(self):
        # Contains tasks.py
        os.chdir('implicit')
        # Doesn't specify --collection
        _output_eq("invoke foo", "Hm\n")

    @trap
    def invocation_with_args(self):
        _output_eq(
            "invoke -c integration print_name --name whatevs",
            "whatevs\n"
        )

    @trap
    def shorthand_binary_name(self):
        _output_eq("invoke -c integration print_foo", "foo\n")

    def core_help_option_prints_core_help(self):
        # TODO: change dynamically based on parser contents?
        # e.g. no core args == no [--core-opts],
        # no tasks == no task stuff?
        expected = """
Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

Core options:
    -c STRING, --collection=STRING        Specify collection name to load. May be given >1 time.
    -h, --help        Show this help message and exit.
    -r STRING, --root=STRING        Change root directory used for finding task modules.

""".lstrip()
        r1 = run("inv -h", hide='out')
        r2 = run("inv --help", hide='out')
        eq_(r1.stdout, expected)
        eq_(r2.stdout, expected)


class HighLevelFailures(Spec):
    def command_failure(self):
        "Command failure doesn't show tracebacks"
        result = run("inv -c fail fail", warn=True)
        sentinel = 'Traceback (most recent call last)'
        assert sentinel not in result.stderr
        assert result.exited != 0

    def parse_failure(self):
        skip()

    def load_failure(self):
        skip()


class CLIParsing(Spec):
    """
    High level parsing tests
    """
    def setup(self):
        @task
        def mytask(mystring, s, boolean=False, b=False, v=False):
            pass
        @task
        def mytask2():
            pass
        @task
        def mytask3(mystring):
            pass
        self.c = Collection(mytask, mytask2, mytask3)

    def _parser(self):
        return Parser(self.c.to_contexts())

    def _parse(self, argstr):
        return self._parser().parse_argv(argstr.split())

    def _compare(self, invoke, flagname, value):
        invoke = "mytask " + invoke
        result = self._parse(invoke)
        eq_(result.to_dict()['mytask'][flagname], value)

    def boolean_args(self):
        "mytask --boolean"
        self._compare("--boolean", 'boolean', True)

    def flag_then_space_then_value(self):
        "mytask --mystring foo"
        self._compare("--mystring foo", 'mystring', 'foo')

    def flag_then_equals_sign_then_value(self):
        "mytask --mystring=foo"
        self._compare("--mystring=foo", 'mystring', 'foo')

    def short_boolean_flag(self):
        "mytask -b"
        self._compare("-b", 'b', True)

    def short_flag_then_space_then_value(self):
        "mytask -s value"
        self._compare("-s value", 's', 'value')

    def short_flag_then_equals_sign_then_value(self):
        "mytask -s=value"
        self._compare("-s=value", 's', 'value')

    def short_flag_with_adjacent_value(self):
        "mytask -svalue"
        r = self._parse("mytask -svalue")
        eq_(r[0].args.s.value, 'value')

    def _flag_value_task(self, value):
        r = self._parse("mytask -s %s mytask2" % value)
        eq_(len(r), 2)
        eq_(r[0].name, 'mytask')
        eq_(r[0].args.s.value, value)
        eq_(r[1].name, 'mytask2')

    def flag_value_then_task(self):
        "mytask -s value mytask2"
        self._flag_value_task('value')

    def flag_value_same_as_task_name(self):
        "mytask -s mytask2 mytask2"
        self._flag_value_task('mytask2')

    def three_tasks_with_args(self):
        "mytask --boolean mytask3 --mystring foo mytask2"
        r = self._parse("mytask --boolean mytask3 --mystring foo mytask2")
        eq_(len(r), 3)
        eq_([x.name for x in r], ['mytask', 'mytask3', 'mytask2'])
        eq_(r[0].args.boolean.value, True)
        eq_(r[1].args.mystring.value, 'foo')

    def tasks_with_duplicately_named_kwargs(self):
        "mytask --mystring foo mytask3 --mystring bar"
        r = self._parse("mytask --mystring foo mytask3 --mystring bar")
        eq_(r[0].name, 'mytask')
        eq_(r[0].args.mystring.value, 'foo')
        eq_(r[1].name, 'mytask3')
        eq_(r[1].args.mystring.value, 'bar')

    def multiple_short_flags_adjacent(self):
        "mytask -bv"
        r = self._parse("mytask -bv")
        a = r[0].args
        eq_(a.b.value, True)
        eq_(a.v.value, True)
