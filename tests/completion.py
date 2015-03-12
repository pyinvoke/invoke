import sys

from nose.tools import ok_

from _utils import (
    _output_eq, IntegrationSpec, _dispatch, trap, expect_exit, assert_contains
)


class ShellCompletion(IntegrationSpec):
    """
    Shell tab-completion behavior
    """

    def no_input_means_just_task_names(self):
        _output_eq('-c simple_ns_list --complete', "z_toplevel\na.b.subtask\n")

    def no_input_with_no_tasks_yields_empty_response(self):
        _output_eq('-c empty --complete', "")

    @trap
    def top_level_with_dash_means_core_options(self):
        with expect_exit(0):
            _dispatch('inv --complete -- -')
        output = sys.stdout.getvalue()
        # No point mirroring all core options, just spot check a few
        for flag in ('--no-dedupe', '-d', '--debug', '-V', '--version'):
            assert_contains(output, "{0}\n".format(flag))
