from spec import Spec, skip, ok_, eq_, raises

from invoke.parser import Parser, Context, Argument
from invoke.collection import Collection


class Parser_(Spec):
    def can_take_initial_context(self):
        c = Context()
        p = Parser(initial=c)
        eq_(p.initial, c)

    def can_take_initial_and_other_contexts(self):
        c1 = Context('foo')
        c2 = Context('bar')
        p = Parser(initial=Context(), contexts=[c1, c2])
        eq_(p.contexts['foo'], c1)
        eq_(p.contexts['bar'], c2)

    def can_take_just_other_contexts(self):
        c = Context('foo')
        p = Parser(contexts=[c])
        eq_(p.contexts['foo'], c)

    def can_take_just_contexts_as_non_keyword_arg(self):
        c = Context('foo')
        p = Parser([c])
        eq_(p.contexts['foo'], c)

    @raises(ValueError)
    def raises_ValueError_for_unnamed_Contexts_in_contexts(self):
        Parser(initial=Context(), contexts=[Context()])

    @raises(ValueError)
    def raises_error_for_context_name_clashes(self):
        Parser(contexts=(Context('foo'), Context('foo')))

    @raises(ValueError)
    def raises_error_for_context_alias_and_name_clashes(self):
        Parser(contexts=(Context('foo', aliases=('bar',)), Context('bar')))

    class parse_argv:
        def parses_sys_argv_style_list_of_strings(self):
            "parses sys.argv-style list of strings"
            # Doesn't-blow-up tests FTL
            mytask = Context(name='mytask')
            mytask.add_arg('--arg')
            p = Parser(contexts=[mytask])
            p.parse_argv(['mytask', '--arg'])

        def returns_only_contexts_mentioned(self):
            task1 = Context('mytask')
            task2 = Context('othertask')
            result = Parser((task1, task2)).parse_argv(['othertask'])
            eq_(len(result), 1)
            eq_(result[0].name, 'othertask')

        def always_includes_initial_context_if_one_was_given(self):
            # Even if no core/initial flags were seen
            t1 = Context('t1')
            init = Context()
            result = Parser((t1,), initial=init).parse_argv(['t1'])
            eq_(result[0].name, None)
            eq_(result[1].name, 't1')

        def returned_contexts_are_in_order_given(self):
            t1, t2 = Context('t1'), Context('t2')
            r = Parser((t1, t2)).parse_argv(['t2', 't1'])
            eq_([x.name for x in r], ['t2', 't1'])

        def returned_context_member_arguments_contain_given_values(self):
            c = Context('mytask', args=('--boolean',))
            result = Parser((c,)).parse_argv(['mytask', '--boolean'])
            eq_(result[0].args['--boolean'].value, True)

        def arguments_which_take_values_get_defaults_overridden_correctly(self):
            args = (Argument('--arg', kind=str), Argument('--arg2', kind=int))
            c = Context('mytask', args=args)
            argv = ['mytask', '--arg', 'myval', '--arg2', '25']
            result = Parser((c,)).parse_argv(argv)
            eq_(result[0].args['--arg'].value, 'myval')
            eq_(result[0].args['--arg2'].value, 25)

        def returned_arguments_not_given_contain_default_values(self):
            # I.e. a Context with args A and B, invoked with no mention of B,
            # should result in B existing in the result, with its default value
            # intact, and not e.g. None, or the arg not existing.
            a = Argument('--name', kind=str)
            b = Argument('--age', default=7)
            c = Context('mytask', args=(a, b))
            result = Parser((c,)).parse_argv(['mytask', '--name', 'blah'])
            eq_(c.args['--age'].value, 7)

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            skip()

        def clones_initial_context(self):
            a = Argument('--foo')
            eq_(a.value, None)
            c = Context(args=(a,))
            p = Parser(initial=c)
            assert p.initial is c
            r = p.parse_argv(['--foo'])
            assert p.initial is c
            c2 = r[0]
            assert c2 is not c
            a2 = c2.args['--foo']
            assert a2 is not a
            eq_(a.value, None)
            eq_(a2.value, True)

        def clones_noninitial_contexts(self):
            a = Argument('--foo')
            eq_(a.value, None)
            c = Context(name='mytask', args=(a,))
            p = Parser(contexts=(c,))
            assert p.contexts['mytask'] is c
            r = p.parse_argv(['mytask', '--foo'])
            assert p.contexts['mytask'] is c
            c2 = r[0]
            assert c2 is not c
            a2 = c2.args['--foo']
            assert a2 is not a
            eq_(a.value, None)
            eq_(a2.value, True)

        def handles_equals_style_long_flags(self):
            c = Context('mytask', args=(Argument('--foo', kind=str),))
            r = Parser((c,)).parse_argv(['mytask', '--foo=bar'])
            eq_(r[0].args['--foo'].value, 'bar')

        def handles_equals_style_short_flags(self):
            c = Context('mytask', args=(Argument('-f', kind=str),))
            r = Parser((c,)).parse_argv(['mytask', '-f=bar'])
            eq_(r[0].args['-f'].value, 'bar')
