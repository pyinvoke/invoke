from _utils import _output_eq, IntegrationSpec


class ShellCompletion(IntegrationSpec):
    """
    Shell tab-completion behavior
    """

    def no_input_means_just_task_names(self):
        _output_eq('-c simple_ns_list --complete', "z_toplevel\na.b.subtask\n")

    def no_input_with_no_tasks_yields_empty_response(self):
        _output_eq('-c empty --complete', "")

    def top_level_with_dash_means_core_options(self):
        _output_eq('--complete -- -', "--lol\n--wut")
