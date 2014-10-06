import os
import sys

from spec import eq_, skip, Spec, ok_, trap, raises
from mock import patch, Mock

from invoke.cli import parse, tasks_from_contexts
from invoke.context import Context
from invoke.runner import run
from invoke.parser import Parser
from invoke.collection import Collection
from invoke.tasks import task
from invoke.exceptions import Failure
import invoke

from _utils import _dispatch, _output_eq, IntegrationSpec, cd, expect_exit


class CLI(IntegrationSpec):
    "Command-line behavior"

    class basic_invocation:
        @trap
        def vanilla(self):
            os.chdir('implicit')
            _dispatch('inv foo')
            eq_(sys.stdout.getvalue(), "Hm\n")

        @trap
        def vanilla_with_explicit_collection(self):
            # Duplicates _output_eq above, but this way that can change w/o
            # breaking our expectations.
            _dispatch('inv -c integration print_foo')
            eq_(sys.stdout.getvalue(), "foo\n")

        def args(self):
            _output_eq('-c integration print_name --name inigo', "inigo\n")

        def underscored_args(self):
            _output_eq(
                '-c integration print_underscored_arg --my-option whatevs',
                "whatevs\n",
            )


    def missing_collection_yields_useful_error(self):
        _output_eq(
            '-c huhwhat -l',
            stderr="Can't find any collection named 'huhwhat'!\n",
            code=1
        )

    def missing_default_collection_doesnt_say_None(self):
        with cd('/'):
            _output_eq(
                '-l',
                stderr="Can't find any collection named 'tasks'!\n",
                code=1
            )

    @trap
    def missing_default_task_prints_help(self):
        with expect_exit():
            _dispatch("inv -c foo")
        ok_("Core options:" in sys.stdout.getvalue())

    def contextualized_tasks_are_given_parser_context_arg(self):
        # go() in contextualized.py just returns its initial arg
        retval = list(_dispatch('invoke -c contextualized go').values())[0]
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
  -c STRING, --collection=STRING   Specify collection name to load.
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
            _output_eq(flag, expected)

    def per_task_help_prints_help_for_task_only(self):
        expected = """
Usage: inv[oke] [--core-opts] punch [--options] [other tasks here ...]

Docstring:
  none

Options:
  -h STRING, --why=STRING   Motive
  -w STRING, --who=STRING   Who to punch

""".lstrip()
        for flag in ['-h', '--help']:
            _output_eq('-c decorator {0} punch'.format(flag), expected)

    def per_task_help_works_for_unparameterized_tasks(self):
        expected = """
Usage: inv[oke] [--core-opts] biz [other tasks here ...]

Docstring:
  none

Options:
  none

""".lstrip()
        _output_eq('-c decorator -h biz', expected)

    def per_task_help_displays_docstrings_if_given(self):
        expected = """
Usage: inv[oke] [--core-opts] foo [other tasks here ...]

Docstring:
  Foo the bar.

Options:
  none

""".lstrip()
        _output_eq('-c decorator -h foo', expected)

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
        _output_eq('-c decorator -h foo2', expected)

    def version_info(self):
        _output_eq('-V', "Invoke %s\n" % invoke.__version__)

    @trap
    def version_override(self):
        with expect_exit():
            _dispatch('notinvoke -V', version="nope 1.0")
        eq_(sys.stdout.getvalue(), "nope 1.0\n")


    class task_list:
        "--list"

        def _listing(self, lines):
            return ("""
Available tasks:

%s

""" % '\n'.join("  " + x for x in lines)).lstrip()

        def _list_eq(self, collection, listing):
            cmd = '-c {0} --list'.format(collection)
            _output_eq(cmd, self._listing(listing))

        def simple_output(self):
            expected = self._listing((
                'bar',
                'biz',
                'boz',
                'foo',
                'post1',
                'post2',
                'print_foo',
                'print_name',
                'print_underscored_arg',
            ))
            for flag in ('-l', '--list'):
                _output_eq('-c integration {0}'.format(flag), expected)

        def namespacing(self):
            self._list_eq('namespacing', (
                'toplevel',
                'module.mytask',
            ))

        def top_level_tasks_listed_first(self):
            self._list_eq('simple_ns_list', (
                'z_toplevel',
                'a.subtask'
            ))

        def subcollections_sorted_in_depth_order(self):
            self._list_eq('deeper_ns_list', (
                'toplevel',
                'a.subtask',
                'a.nother.subtask',
            ))

        def aliases_sorted_alphabetically(self):
            self._list_eq('alias_sorting', (
                'toplevel (a, z)',
            ))

        def default_tasks(self):
            # sub-ns default task display as "real.name (collection name)"
            self._list_eq('explicit_root', (
                'top_level (othertop)',
                'sub.sub_task (sub, sub.othersub)',
            ))

        def docstrings_shown_alongside(self):
            self._list_eq('docstrings', (
                'leading_whitespace    foo',
                'no_docstring',
                'one_line              foo',
                'two_lines             foo',
                'with_aliases (a, b)   foo',
            ))

        def empty_collections_say_no_tasks(self):
            _output_eq(
                "-c empty -l",
                "No tasks found in collection 'empty'!\n"
            )


    def debug_flag_activates_logging(self):
        # Have to patch our logger to get in before Nose logcapture kicks in.
        with patch('invoke.util.debug') as debug:
            _dispatch('inv -d -c debugging foo')
            debug.assert_called_with('my-sentinel')


    class autoprinting:
        def defaults_to_off_and_no_output(self):
            _output_eq("-c autoprint nope", "")

        def prints_return_value_to_stdout_when_on(self):
            _output_eq("-c autoprint yup", "It's alive!\n")

        def prints_return_value_to_stdout_when_on_and_in_collection(self):
            _output_eq("-c autoprint sub.yup", "It's alive!\n")

        def does_not_fire_on_pre_tasks(self):
            _output_eq("-c autoprint pre_check", "")

        def does_not_fire_on_post_tasks(self):
            _output_eq("-c autoprint post_check", "")


    class run_options:
        "run() related CLI flags"
        def _test_flag(self, flag, kwarg, value):
            with patch('invoke.context.run') as run:
                _dispatch('invoke {0} -c contextualized run'.format(flag))
                run.assert_called_with('x', **{kwarg: value})

        def warn_only(self):
            self._test_flag('-w', 'warn', True)

        def pty(self):
            self._test_flag('-p', 'pty', True)

        def hide(self):
            self._test_flag('--hide both', 'hide', 'both')

        def echo(self):
            self._test_flag('-e', 'echo', True)


    class configuration:
        "Configuration-related concerns"

        def per_project_config_files_are_loaded(self):
            # Just reuse an existing project bit
            with cd(os.path.join('configs', 'project', 'yaml-only')):
                _dispatch("inv mytask")

        def runtime_config_file_honored(self):
            with cd(os.path.join('configs', 'runtime')):
                _dispatch("inv -f runtime.yaml mytask")


TB_SENTINEL = 'Traceback (most recent call last)'

class HighLevelFailures(Spec):
    @trap
    def command_failure(self):
        "Command failure doesn't show tracebacks"
        with patch('sys.exit') as exit:
            _dispatch('inv -c fail simple')
            assert TB_SENTINEL not in sys.stderr.getvalue()
            exit.assert_called_with(1)

    class parsing:
        @trap
        def should_not_show_tracebacks(self):
            # Ensure we fall out of dispatch() on missing parser args,
            # but are still able to look at stderr to ensure no TB got printed
            with patch('sys.exit', Mock(side_effect=SystemExit)):
                try:
                    _dispatch("inv -c fail missing_pos")
                except SystemExit:
                    pass
                assert TB_SENTINEL not in sys.stderr.getvalue()

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
        @task(default=True)
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

    def loaded_collection_default_task(self):
        result = tasks_from_contexts(self._parse(''), self.c)
        eq_(len(result), 1)
        eq_(result[0][0], 'mytask3')

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
