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
            Parser(initial=Context(), contexts=[Context()]).parse_argv(['mytask', '--arg'])

        def returns_ordered_list_of_tasks_and_their_args(self):
            skip()

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            skip()


class Argument_(Spec):
    def may_have_long_name(self):
        skip()

    def may_have_short_name(self):
        skip()

    def must_have_at_least_one_name(self):
        skip()

    class answers_to:
        def returns_True_if_given_name_matches(self):
            skip()

    class coerce:
        def transforms_string_value_to_Python_object(self):
            skip()


class Context_(Spec):
    class add_arg:
        def can_take_Argument_instance(self):
            c = Context()
            a = Argument(long_name='foo')
            c.add_arg(a)
            eq_(c.get_arg('foo'), a)

        def can_take_kwargs(self):
            c = Context()
            c.add_arg(long_name='foo')
            eq_(c.get_arg('foo').long_name, 'foo')

        def raises_some_Exception_on_duplicate(self):
            skip()

    class has_arg:
        def returns_True_if_flag_is_valid_arg(self):
            c = Context()
            c.add_arg(Argument(long_name='foo'))
            eq_(c.has_arg('foo'), True)

    class needs_value:
        def returns_whether_given_flag_needs_a_value(self):
            c = Context()
            c.add_arg(Argument(long_name='foo', needs_value=True))
            eq_(c.needs_value('foo'), True)
