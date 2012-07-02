import os
import sys
import StringIO

from spec import eq_, skip, Spec, raises, ok_

from invoke import run
from invoke.parser import Parser, Context
from invoke.collection import Collection
from invoke.task import task
from invoke.exceptions import Failure

from _utils import support


class CLI(Spec):
    "Command-line behavior"
    def setup(self):
        os.chdir(support)
        sys.stdout, self.orig_stdout = StringIO.StringIO(), sys.stdout
        sys.stderr, self.orig_stderr = StringIO.StringIO(), sys.stderr
        self.result = run("invoke -c integration print_foo")

    def teardown(self):
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr

    # Yo dogfood, I heard you like invoking
    def basic_invocation(self):
        eq_(self.result.stdout, "foo\n")

    def implicit_task_module(self):
        # Contains tasks.py
        os.chdir('implicit')
        # Doesn't specify --collection
        result = run("invoke foo")
        eq_(result.stdout, "Hm\n")

    def invocation_with_args(self):
        result = run("invoke -c integration print_name --name whatevs")
        eq_(result.stdout, "whatevs\n")

    def shorthand_binary_name(self):
        eq_(self.result.stdout, "foo\n")

    def return_code_in_result(self):
        eq_(self.result.stdout, "foo\n")
        eq_(self.result.return_code, 0)
        eq_(self.result.exited, 0)

    def nonzero_return_code_for_failures(self):
        result = run("false", warn=True)
        eq_(result.exited, 1)
        result = run("goobypls", warn=True)
        eq_(result.exited, 127)

    @raises(Failure)
    def fast_failures(self):
        run("false")

    def run_acts_as_success_boolean(self):
        ok_(not run("false", warn=True))
        ok_(run("true"))

    def non_one_return_codes_still_act_as_False(self):
        ok_(not run("goobypls", warn=True))


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
        c = Collection()
        c.add_task('mytask', mytask)
        c.add_task('mytask2', mytask2)
        c.add_task('mytask3', mytask3)
        self.c = c

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
