import sys

from invoke import Program

from spec import assert_contains, assert_not_contains, eq_

from _util import (
    expect, IntegrationSpec, trap
)


@trap
def _complete(invocation, collection=None):
    colstr = ""
    if collection:
        colstr = "-c {0}".format(collection)
    command = "inv --complete {0} -- inv {0} {1}".format(colstr, invocation)
    Program().run(command, exit=False)
    return sys.stdout.getvalue()


class CompletionScriptPrinter(IntegrationSpec):
    """
    Printing the completion script
    """

    def prints_for_invoke(self):
        expect(
            '--print-completion-script bash',
            program=Program(binary='inv[oke]'),
            out="inv invoke", test=assert_contains
        )

    def only_accepts_certain_console_types(self):
        expect(
            '--print-completion-script',
            err="needed value and was not given one", test=assert_contains
        )
        expect(
            '--print-completion-script bla',
            err="not supported. Choose either", test=assert_contains
        )

    def prints_for_custom_binary(self):
        expect(
            'myapp --print-completion-script zsh',
            program=Program(binary='mya[pp]'),
            invoke=False,
            out="mya myapp", test=assert_contains
        )


class ShellCompletion(IntegrationSpec):
    """
    Shell tab-completion behavior
    """

    def no_input_means_just_task_names(self):
        expect(
            '-c simple_ns_list --complete',
            out="z-toplevel\na.b.subtask\n"
        )

    def custom_binary_name_completes(self):
        expect(
            'myapp -c integration --complete -- ba',
            program=Program(binary='myapp'),
            invoke=False,
            out="bar", test=assert_contains
        )

    def aliased_custom_binary_name_completes(self):
        for used_binary in ('my', 'myapp'):
            expect(
                '{0} -c integration --complete -- ba'.format(used_binary),
                program=Program(binary='my[app]'),
                invoke=False,
                out="bar", test=assert_contains
            )

    def no_input_with_no_tasks_yields_empty_response(self):
        expect('-c empty --complete', out="")

    def task_name_completion_includes_aliases(self):
        for name in ('z\n', 'toplevel'):
            assert_contains(_complete('', 'alias_sorting'), name)

    def top_level_with_dash_means_core_options(self):
        output = _complete('-')
        # No point mirroring all core options, just spot check a few
        for flag in ('--no-dedupe', '-d', '--debug', '-V', '--version'):
            assert_contains(output, "{0}\n".format(flag))

    def bare_double_dash_shows_only_long_core_options(self):
        output = _complete('--')
        assert_contains(output, '--no-dedupe')
        assert_not_contains(output, '-V')

    def task_names_only_complete_other_task_names(self):
        # Because only tokens starting with a dash should result in options.
        assert_contains(_complete('print-foo', 'integration'), 'print-name')

    def task_name_completion_includes_tasks_already_seen(self):
        # Because it's valid to call the same task >1 time.
        assert_contains(_complete('print-foo', 'integration'), 'print-foo')

    def per_task_flags_complete_with_single_dashes(self):
        for flag in ('--name', '-n'):
            assert_contains(_complete('print-name -', 'integration'), flag)

    def per_task_flags_complete_with_double_dashes(self):
        output = _complete('print-name --', 'integration')
        assert_contains(output, '--name')
        assert_not_contains(output, '-n\n') # newline because -n is in --name

    def flag_completion_includes_inverse_booleans(self):
        output = _complete('basic-bool -', 'foo')
        assert_contains(output, '--no-mybool')

    def tasks_with_positional_args_complete_with_flags(self):
        # Because otherwise completing them is invalid anyways.
        # NOTE: this currently duplicates another test because this test cares
        # about a specific detail.
        output = _complete('print-name --', 'integration')
        assert_contains(output, '--name')

    def core_flags_taking_values_have_no_completion_output(self):
        # So the shell's default completion is available.
        eq_(_complete('-f'), '')

    def per_task_flags_taking_values_have_no_completion_output(self):
        eq_(_complete('basic-arg --arg', 'foo'), '')

    def core_bool_flags_have_task_name_completion(self):
        assert_contains(_complete('--echo', 'foo'), 'mytask')

    def per_task_bool_flags_have_task_name_completion(self):
        assert_contains(_complete('basic-bool --mybool', 'foo'), 'mytask')

    def core_partial_or_invalid_flags_print_all_flags(self):
        for flag in ('--echo', '--complete'):
            for given in ('--e', '--nope'):
                assert_contains(_complete(given), flag)

    def per_task_partial_or_invalid_flags_print_all_flags(self):
        for flag in ('--arg1', '--otherarg'):
            for given in ('--ar', '--nope'):
                assert_contains(
                    _complete('multiple-args {0}'.format(given), 'foo'),
                    flag
                )
