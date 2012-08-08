from spec import Spec, skip, ok_, eq_, raises, trap

from invoke.parser import Parser, Context, Argument, ParseError, ParserHelp
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
        Parser((Context('foo', aliases=('bar',)), Context('bar')))

    @raises(ValueError)
    def raises_error_for_context_name_and_alias_clashes(self):
        # I.e. inverse of the above, which is a different code path.
        Parser((Context('foo'), Context('bar', aliases=('foo',))))

    def takes_ignore_unknown_kwarg(self):
        Parser(ignore_unknown=True)

    def ignore_unknown_defaults_to_False(self):
        eq_(Parser().ignore_unknown, False)

    class parse_argv:
        def parses_sys_argv_style_list_of_strings(self):
            "parses sys.argv-style list of strings"
            # Doesn't-blow-up tests FTL
            mytask = Context(name='mytask')
            mytask.add_arg('arg')
            p = Parser(contexts=[mytask])
            p.parse_argv(['mytask', '--arg', 'value'])

        def returns_only_contexts_mentioned(self):
            task1 = Context('mytask')
            task2 = Context('othertask')
            result = Parser((task1, task2)).parse_argv(['othertask'])
            eq_(len(result), 1)
            eq_(result[0].name, 'othertask')

        @raises(ParseError)
        def raises_error_if_unknown_contexts_found(self):
            Parser().parse_argv(['foo', 'bar'])

        def unparsed_does_not_share_state(self):
            r = Parser(ignore_unknown=True).parse_argv(['self'])
            eq_(r.unparsed, ['self'])
            r2 = Parser(ignore_unknown=True).parse_argv(['contained'])
            eq_(r.unparsed, ['self']) # NOT ['self', 'contained']
            eq_(r2.unparsed, ['contained']) # NOT ['self', 'contained']

        def ignore_unknown_returns_unparsed_argv_instead(self):
            r = Parser(ignore_unknown=True).parse_argv(['foo', 'bar', '--baz'])
            eq_(r.unparsed, ['foo', 'bar', '--baz'])

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
            c = Context('mytask', args=(Argument('boolean', kind=bool),))
            result = Parser((c,)).parse_argv(['mytask', '--boolean'])
            eq_(result[0].args['boolean'].value, True)

        def arguments_which_take_values_get_defaults_overridden_correctly(self):
            args = (Argument('arg', kind=str), Argument('arg2', kind=int))
            c = Context('mytask', args=args)
            argv = ['mytask', '--arg', 'myval', '--arg2', '25']
            result = Parser((c,)).parse_argv(argv)
            eq_(result[0].args['arg'].value, 'myval')
            eq_(result[0].args['arg2'].value, 25)

        def returned_arguments_not_given_contain_default_values(self):
            # I.e. a Context with args A and B, invoked with no mention of B,
            # should result in B existing in the result, with its default value
            # intact, and not e.g. None, or the arg not existing.
            a = Argument('name', kind=str)
            b = Argument('age', default=7)
            c = Context('mytask', args=(a, b))
            result = Parser((c,)).parse_argv(['mytask', '--name', 'blah'])
            eq_(c.args['age'].value, 7)

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            r = Parser((Context('foo'),)).parse_argv(['foo', '--', 'bar', 'biz'])
            eq_(r.remainder, "bar biz")

        def clones_initial_context(self):
            a = Argument('foo', kind=bool)
            eq_(a.value, None)
            c = Context(args=(a,))
            p = Parser(initial=c)
            assert p.initial is c
            r = p.parse_argv(['--foo'])
            assert p.initial is c
            c2 = r[0]
            assert c2 is not c
            a2 = c2.args['foo']
            assert a2 is not a
            eq_(a.value, None)
            eq_(a2.value, True)

        def clones_noninitial_contexts(self):
            a = Argument('foo')
            eq_(a.value, None)
            c = Context(name='mytask', args=(a,))
            p = Parser(contexts=(c,))
            assert p.contexts['mytask'] is c
            r = p.parse_argv(['mytask', '--foo', 'val'])
            assert p.contexts['mytask'] is c
            c2 = r[0]
            assert c2 is not c
            a2 = c2.args['foo']
            assert a2 is not a
            eq_(a.value, None)
            eq_(a2.value, 'val')

        class equals_signs:
            def _compare(self, argname, invoke, value):
                c = Context('mytask', args=(Argument(argname, kind=str),))
                r = Parser((c,)).parse_argv(['mytask', invoke])
                eq_(r[0].args[argname].value, value)

            def handles_equals_style_long_flags(self):
                self._compare('foo', '--foo=bar', 'bar')

            def handles_equals_style_short_flags(self):
                self._compare('f', '-f=bar', 'bar')

            def does_not_require_escaping_equals_signs_in_value(self):
                self._compare('f', '-f=biz=baz', 'biz=baz')

        def handles_multiple_boolean_flags_per_context(self):
            c = Context('mytask', args=(
                Argument('foo', kind=bool), Argument('bar', kind=bool)
            ))
            r = Parser((c,)).parse_argv(['mytask', '--foo', '--bar'])
            a = r[0].args
            eq_(a.foo.value, True)
            eq_(a.bar.value, True)


class ParseResult_(Spec):
    "ParseResult"
    def setup(self):
        self.context = Context('mytask',
            args=(Argument('foo', kind=str), Argument('bar')))
        argv = ['mytask', '--foo', 'foo-val', '--', 'my', 'remainder']
        self.result = Parser((self.context,)).parse_argv(argv)

    def acts_as_a_list_of_parsed_contexts(self):
        eq_(len(self.result), 1)
        eq_(self.result[0].name, 'mytask')

    def exhibits_remainder_attribute(self):
        eq_(self.result.remainder, 'my remainder')

    def to_dict_returns_parsed_contexts_and_args_as_nested_dicts(self):
        eq_(
            self.result.to_dict(),
            {'mytask': {'foo': 'foo-val', 'bar': None}}
        )
