from _utils import _output_eq, IntegrationSpec


class ShellCompletion(IntegrationSpec):
    """
    Shell tab-completion related flags
    """

    class tasks:
        "--tasks"

        def tasks_flag_prints_all_tasks(self):
            _output_eq('-c simple_ns_list --tasks', "z_toplevel\na.b.subtask\n")

        def empty_tasks_have_empty_output(self):
            _output_eq('-c empty --tasks', "")
