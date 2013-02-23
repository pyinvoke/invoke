import os
import sys

from spec import eq_, skip, Spec, ok_, trap

from invoke.cli import parse
from invoke.runner import run
from invoke.parser import Parser, Context
from invoke.collection import Collection
from invoke.tasks import task
from invoke.exceptions import Failure
import invoke

from _utils import support


def _output_eq(cmd, expected):
    return eq_(run(cmd).stdout, expected)


class CLI(Spec):
    "Command-line behavior"
    def setup(self):
        os.chdir(support)
        self.result = run("invoke -c integration print_foo", hide='both')

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
        # NOTE: test will trigger default pty size of 80x24, so the below
        # string is formatted appropriately.
        # TODO: add more unit-y tests for specific behaviors:
        # * fill terminal w/ columns + spacing
        # * line-wrap help text in its own column
        expected = """
Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

Core options:
  -c STRING, --collection=STRING   Specify collection name to load. May be
                                   given >1 time.
  -h, --help                       Show this help message and exit.
  -l, --list                       List available tasks.
  -r STRING, --root=STRING         Change root directory used for finding task
                                   modules.
  -V, --version                    Show version and exit

""".lstrip()
        r1 = run("inv -h", hide='out')
        r2 = run("inv --help", hide='out')
        eq_(r1.stdout, expected)
        eq_(r2.stdout, expected)

    @trap
    def version_info(self):
        eq_(run("invoke -V").stdout, "Invoke %s\n" % invoke.__version__)

    @trap
    def task_list(self):
        expected = """
Available tasks:

    print_foo
    print_name

""".lstrip()
        for flag in ('-l', '--list'):
            eq_(run("invoke -c integration %s" % flag).stdout, expected)


TB_SENTINEL = 'Traceback (most recent call last)'

class HighLevelFailures(Spec):

    def command_failure(self):
        "Command failure doesn't show tracebacks"
        result = run("inv -c fail simple", warn=True, hide='both')
        assert TB_SENTINEL not in result.stderr
        assert result.exited != 0

    class parsing:
        def should_not_show_tracebacks(self):
            result = run("inv -c fail missing_pos", warn=True, hide='both')
            assert TB_SENTINEL not in result.stderr

        def should_show_core_usage_on_core_failures(self):
            skip()

        def should_show_context_usage_on_context_failures(self):
            skip()

    def load_failure(self):
        skip()


class CLIParsing(Spec):
    """
    High level parsing tests
    """
    def setup(self):
        @task(positional=[])
        def mytask(mystring, s, boolean=False, b=False, v=False):
            pass
        @task
        def mytask2():
            pass
        @task
        def mytask3(mystring):
            pass
        @task
        def mytask4(clean=False, browse=False):
            pass
        self.c = Collection(mytask, mytask2, mytask3, mytask4)

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
        "mytask -bv (and inverse)"
        for args in ('-bv', '-vb'):
            r = self._parse("mytask %s" % args)
            a = r[0].args
            eq_(a.b.value, True)
            eq_(a.v.value, True)

    def globbed_shortflags_with_multipass_parsing(self):
        "mytask -cb and -bc"
        for args in ('-bc', '-cb'):
            _, _, r = parse(['mytask4', args], self.c)
            a = r[0].args
            eq_(a.clean.value, True)
            eq_(a.browse.value, True)
