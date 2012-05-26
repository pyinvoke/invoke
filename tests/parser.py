from spec import Spec, skip, ok_, eq_, raises

from invoke.parser import Parser, Context, Argument
from invoke.collection import Collection


class Parser_(Spec):
    def has_and_requires_initial_context(self):
        c = Context()
        p = Parser(initial=c)
        eq_(p.initial, c)

    def may_also_take_additional_contexts(self):
        c1 = Context('foo')
        c2 = Context('bar')
        p = Parser(initial=Context(), contexts=[c1, c2])
        eq_(p.contexts['foo'], c1)
        eq_(p.contexts['bar'], c2)

    @raises(ValueError)
    def raises_ValueError_for_unnamed_Contexts_in_contexts(self):
        Parser(initial=Context(), contexts=[Context()])

    class parse_argv:
        def parses_sys_argv_style_list_of_strings(self):
            "parses sys.argv-style list of strings"
            # Doesn't-blow-up tests FTL
            mytask = Context(name='mytask')
            mytask.add_arg('--arg')
            p = Parser(contexts=[mytask])
            p.parse_argv(['mytask', '--arg'])

        def returns_ordered_list_of_tasks_and_their_args(self):
            skip()

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            skip()
