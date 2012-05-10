from spec import Spec, skip, ok_, eq_, raises

from invoke.parser import Parser, Context, Argument
from invoke.collection import Collection


class Parser_(Spec):
    class init:
        "__init__"
        def requires_initial_context(self):
            c = Context()
            p = Parser(initial=c)
            eq_(p.initial, c)

        def may_also_take_additional_contexts(self):
            c1 = Context()
            c2 = Context()
            p = Parser(initial=c1, contexts=[c2])
            eq_(p.contexts[0], c2)

    class parse_argv:
        def parses_sys_argv_style_list_of_strings(self):
            "parses sys.argv-style list of strings"
            # Doesn't-blow-up tests FTL
            p = Parser(initial=Context(), contexts=[Context()])
            p.parse_argv(['mytask', '--arg'])

        def returns_ordered_list_of_tasks_and_their_args(self):
            skip()

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            skip()
