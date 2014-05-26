import os
import sys

from spec import eq_, skip, Spec, ok_, trap
from mock import patch

from invoke.cli import parse, dispatch
from invoke.context import Context
from invoke.runner import run
from invoke.parser import Parser
from invoke.collection import Collection
from invoke.tasks import task
from invoke.exceptions import Failure
import invoke

from _utils import support


@trap
def _output_eq(args, expect_stdout=None, expect_stderr=None):
    """
    dispatch() 'args', matching output to 'expect_std(out|err)'.

    Must give either or both of the 'expect' args.
    """
    args = ['inv'] + args
    dispatch(args)
    if expect_stdout:
        eq_(sys.stdout.getvalue(), expect_stdout)
    if expect_stderr:
        eq_(sys.stderr.getvalue(), expect_stderr)


class CLI(Spec):
    "Command-line behavior"
    def setup(self):
        os.chdir(support)

    class basic_invocation:
        @trap
        def vanilla(self):
            os.chdir('implicit')
            dispatch(['inv', 'foo'])
            eq_(sys.stdout.getvalue(), "Hm\n")

        @trap
        def vanilla_with_explicit_collection(self):
            # Duplicates _output_eq above, but this way that can change w/o
            # breaking our expectations.
            dispatch(['inv', '-c', 'integration', 'print_foo'])
            eq_(sys.stdout.getvalue(), "foo\n")

        def args(self):
            _output_eq(
                ['-c', 'integration', 'print_name', '--name', 'inigo'],
                "inigo\n",
            )

        def underscored_args(self):
            _output_eq(
                ['-c', 'integration',
                    'print_underscored_arg', '--my-option', 'whatevs'],
                "whatevs\n",
            )

    def contextualized_tasks_are_given_parser_context_arg(self):
        # go() in contextualized.py just returns its initial arg
        retval = dispatch(['invoke', '-c', 'contextualized', 'go'])[0]
        assert isinstance(retval, Context)

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
  --no-dedupe                      Disable task deduplication.
  -c STRING, --collection=STRING   Specify collection name to load. May be
                                   given >1 time.
  -d, --debug                      Enable debug output.
  -e, --echo                       Echo executed commands before running.
  -h [STRING], --help[=STRING]     Show core or per-task help and exit.
  -H STRING, --hide=STRING         Set default value of run()'s 'hide' kwarg.
  -l, --list                       List available tasks.
  -p, --pty                        Use a pty when executing shell commands.
  -r STRING, --root=STRING         Change root directory used for finding task
                                   modules.
  -V, --version                    Show version and exit.
  -w, --warn-only                  Warn, instead of failing, when shell
                                   commands fail.

""".lstrip()
        for flag in ['-h', '--help']:
            with patch('sys.exit'):
                _output_eq([flag], expect_stdout=expected)

    @trap
    def per_task_help_prints_help_for_task_only(self):
        expected = """
Usage: inv[oke] [--core-opts] punch [--options] [other tasks here ...]

Docstring:
  none

Options:
  -h STRING, --why=STRING   Motive
  -w STRING, --who=STRING   Who to punch

""".lstrip()
        r1 = run("inv -c decorator -h punch", hide='out')
        r2 = run("inv -c decorator --help punch", hide='out')
        eq_(r1.stdout, expected)
        eq_(r2.stdout, expected)

    @trap
    def per_task_help_works_for_unparameterized_tasks(self):
        expected = """
Usage: inv[oke] [--core-opts] biz [other tasks here ...]

Docstring:
  none

Options:
  none

""".lstrip()
        r = run("inv -c decorator -h biz", hide='out')
        eq_(r.stdout, expected)

    @trap
    def per_task_help_displays_docstrings_if_given(self):
        expected = """
Usage: inv[oke] [--core-opts] foo [other tasks here ...]

Docstring:
  Foo the bar.

Options:
  none

""".lstrip()
        r = run("inv -c decorator -h foo", hide='out')
        eq_(r.stdout, expected)

    @trap
    def per_task_help_dedents_correctly(self):
        expected = """
Usage: inv[oke] [--core-opts] foo2 [other tasks here ...]

Docstring:
  Foo the bar:

    example code

  Added in 1.0

Options:
  none

""".lstrip()
        r = run("inv -c decorator -h foo2", hide='out')
        eq_(r.stdout, expected)

    @trap
    def version_info(self):
        eq_(run("invoke -V").stdout, "Invoke %s\n" % invoke.__version__)

    @trap
    def version_override(self):
        with patch('sys.exit') as exit: # TODO: sigh.
            parse(['notinvoke', '-V'], Collection(), "nope 1.0")
            assert 'nope 1.0' in sys.stdout.getvalue()

    class task_list:
        "--list"

        def _listing(self, *lines):
            return ("""
Available tasks:

%s

""" % '\n'.join("  " + x for x in lines)).lstrip()

        @trap
        def simple_output(self):
            expected = self._listing(
                'bar',
                'foo',
                'print_foo',
                'print_name',
                'print_underscored_arg',
            )
            for flag in ('-l', '--list'):
                eq_(run("invoke -c integration %s" % flag).stdout, expected)

        @trap
        def namespacing(self):
            # TODO: break out the listing behavior into a testable method, down
            # with subprocesses!
            expected = self._listing(
                'toplevel',
                'module.mytask',
            )
            eq_(run("invoke -c namespacing --list").stdout, expected)

        @trap
        def top_level_tasks_listed_first(self):
            expected = self._listing(
                'z_toplevel',
                'a.subtask'
            )
            eq_(run("invoke -c simple_ns_list --list").stdout, expected)

        @trap
        def subcollections_sorted_in_depth_order(self):
            expected = self._listing(
                'toplevel',
                'a.subtask',
                'a.nother.subtask',
            )
            eq_(run("invoke -c deeper_ns_list --list").stdout, expected)

        @trap
        def aliases_sorted_alphabetically(self):
            expected = self._listing(
                'toplevel (a, z)',
            )
            eq_(run("invoke -c alias_sorting --list").stdout, expected)


        @trap
        def default_tasks(self):
            # sub-ns default task display as "real.name (collection name)"
            expected = self._listing(
                'top_level (othertop)',
                'sub.sub_task (sub, sub.othersub)',
            )
            eq_(run("invoke -c explicit_root --list").stdout, expected)

        @trap
        def docstrings_shown_alongside(self):
            expected = self._listing(
                'leading_whitespace    foo',
                'no_docstring',
                'one_line              foo',
                'two_lines             foo',
                'with_aliases (a, b)   foo',
            )
            eq_(run("invoke -c docstrings --list").stdout, expected)

    @trap
    def no_deduping(self):
        expected = """
foo
foo
bar
""".lstrip()
        eq_(run("invoke -c integration --no-dedupe foo bar").stdout, expected)

    @trap
    def debug_flag(self):
        assert 'my-sentinel' in run("invoke -d -c debugging foo").stderr

    class run_options:
        "run() related CLI flags"
        def _test_flag(self, flag, kwarg, value):
            with patch('invoke.context.run') as run:
                dispatch(['invoke'] + flag + ['-c', 'contextualized', 'run'])
                run.assert_called_with('x', **{kwarg: value})

        def warn_only(self):
            self._test_flag(['-w'], 'warn', True)

        def pty(self):
            self._test_flag(['-p'], 'pty', True)

        def hide(self):
            self._test_flag(['--hide', 'both'], 'hide', 'both')

        def echo(self):
            self._test_flag(['-e'], 'echo', True)


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
        def mytask(mystring, s, boolean=False, b=False, v=False,
            long_name=False, true_bool=True):
            pass
        @task(aliases=['mytask27'])
        def mytask2():
            pass
        @task
        def mytask3(mystring):
            pass
        @task
        def mytask4(clean=False, browse=False):
            pass
        @task(aliases=['other'], default=True)
        def subtask():
            pass
        subcoll = Collection('sub', subtask)
        self.c = Collection(mytask, mytask2, mytask3, mytask4, subcoll)

    def _parser(self):
        return Parser(self.c.to_contexts())

    def _parse(self, argstr):
        return self._parser().parse_argv(argstr.split())

    def _compare(self, invoke, flagname, value):
        invoke = "mytask " + invoke
        result = self._parse(invoke)
        eq_(result[0].args[flagname].value, value)

    def _compare_names(self, given, real):
        eq_(self._parse(given)[0].name, real)

    def underscored_flags_can_be_given_as_dashed(self):
        self._compare('--long-name', 'long_name', True)

    def inverse_boolean_flags(self):
        self._compare('--no-true-bool', 'true_bool', False)

    def namespaced_task(self):
        self._compare_names("sub.subtask", "sub.subtask")

    def aliases(self):
        self._compare_names("mytask27", "mytask2")

    def subcollection_aliases(self):
        self._compare_names("sub.other", "sub.subtask")

    def subcollection_default_tasks(self):
        self._compare_names("sub", "sub.subtask")

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
            _, _, r = parse(['invoke', 'mytask4', args], self.c)
            a = r[0].args
            eq_(a.clean.value, True)
            eq_(a.browse.value, True)
