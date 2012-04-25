from spec import Spec, skip

from invoke.parser import Parser

class Parser_(Spec):
    class init:
        "__init__"
        def takes_a_collection_to_use_when_parsing_task_flags(self):
            skip()

    class parse_argv:
        def parses_sys_argv_style_list_of_strings(self):
            "parses sys.argv-style list of strings"
            skip()

        def returns_ordered_list_of_tasks_and_their_args(self):
            skip()

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            skip()

    class parse_string:
        def parses_a_shell_command_string(self):
            skip()

        def proxies_to_self_parse_argv(self):
            "proxies to self.parse_argv()"
            skip()
