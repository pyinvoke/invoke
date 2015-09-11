import os
import sys

from spec import eq_, skip, Spec, ok_, trap
from mock import patch, Mock

from invoke.cli import tasks_from_contexts
from invoke.collection import Collection
from invoke.context import Context
from invoke.parser import Parser
from invoke.tasks import task

from _utils import (
    _dispatch, _output_eq, IntegrationSpec, cd, expect_exit,
    skip_if_windows, mocked_run
)


class CLI(IntegrationSpec):
    "Command-line behavior"

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
        "run() related CLI flags affect 'run' config values"
        def _test_flag(self, flag, key):
            with mocked_run():
                # The tasks themselves perform the necessary asserts.
                _dispatch('invoke {0} -c contextualized check_{1}'.format(
                    flag, key
                ))

        def warn_only(self):
            self._test_flag('-w', 'warn')

        def pty(self):
            self._test_flag('-p', 'pty')

        def hide(self):
            self._test_flag('--hide both', 'hide')

        def echo(self):
            self._test_flag('-e', 'echo')

    class configuration:
        "Configuration-related concerns"

        def per_project_config_files_are_loaded(self):
            with cd(os.path.join('configs', 'yaml')):
                _dispatch("inv mytask")

        def per_project_config_files_load_with_explicit_ns(self):
            # Re: #234
            with cd(os.path.join('configs', 'yaml')):
                _dispatch("inv -c explicit mytask")

        def runtime_config_file_honored(self):
            with cd('configs'):
                _dispatch("inv -c runtime -f yaml/invoke.yaml mytask")

        def tasks_dedupe_honors_configuration(self):
            # Kinda-sorta duplicates some tests in executor.py, but eh.
            with cd('configs'):
                # Runtime conf file
                _output_eq(
                    '-c integration -f no-dedupe.yaml biz',
                    """
foo
foo
bar
biz
post1
post2
post2
""".lstrip())
                # Flag beats runtime
                _output_eq(
                    '-c integration -f dedupe.yaml --no-dedupe biz',
                    """
foo
foo
bar
biz
post1
post2
post2
""".lstrip())

        # * debug (top level?)
        # * hide (run.hide...lol)
        # * pty (run.pty)
        # * warn (run.warn)

        def env_vars_load_with_prefix(self):
            os.environ['INVOKE_RUN_ECHO'] = "1"
            with mocked_run():
                # Task performs the assert
                _dispatch('invoke -c contextualized check_echo')


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
        r = self._parse("mytask -s {0} mytask2".format(value))
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
            r = self._parse("mytask {0}".format(args))
            a = r[0].args
            eq_(a.b.value, True)
            eq_(a.v.value, True)
