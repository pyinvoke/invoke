from spec import Spec, eq_, raises, skip, ok_

from invoke.parser import Parser, Context, Argument, ParseError


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

        def ignore_unknown_does_not_mutate_rest_of_argv(self):
            p = Parser([Context('ugh')], ignore_unknown=True)
            r = p.parse_argv(['ugh', 'what', '-nowai'])
            # NOT: ['what', '-n', '-w', '-a', '-i']
            eq_(r.unparsed, ['what', '-nowai'])

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

        def inverse_bools_get_set_correctly(self):
            arg = Argument('myarg', kind=bool, default=True)
            c = Context('mytask', args=(arg,))
            r = Parser((c,)).parse_argv(['mytask', '--no-myarg'])
            eq_(r[0].args['myarg'].value, False)

        def arguments_which_take_values_get_defaults_overridden_correctly(self): # noqa
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
            Parser((c,)).parse_argv(['mytask', '--name', 'blah'])
            eq_(c.args['age'].value, 7)

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            r = Parser((Context('foo'),)).parse_argv(
                ['foo', '--', 'bar', 'biz']
            )
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

        class parsing_errors:
            def setup(self):
                self.p = Parser([Context(name='foo', args=[Argument('bar')])])

            @raises(ParseError)
            def missing_flag_values_raise_ParseError(self):
                self.p.parse_argv(['foo', '--bar'])

            def attaches_context_to_ParseErrors(self):
                try:
                    self.p.parse_argv(['foo', '--bar'])
                except ParseError as e:
                    assert e.context is not None

            def attached_context_is_None_outside_contexts(self):
                try:
                    Parser().parse_argv(['wat'])
                except ParseError as e:
                    assert e.context is None

        class positional_arguments:
            def _basic(self):
                arg = Argument('pos', positional=True)
                mytask = Context(name='mytask', args=[arg])
                return Parser(contexts=[mytask])

            def single_positional_arg(self):
                r = self._basic().parse_argv(['mytask', 'posval'])
                eq_(r[0].args['pos'].value, 'posval')

            @raises(ParseError)
            def omitted_positional_arg_raises_ParseError(self):
                self._basic().parse_argv(['mytask'])

            def positional_args_eat_otherwise_valid_context_names(self):
                mytask = Context('mytask', args=[
                    Argument('pos', positional=True),
                    Argument('nonpos', default='default')
                ])
                Context('lolwut')
                result = Parser([mytask]).parse_argv(['mytask', 'lolwut'])
                r = result[0]
                eq_(r.args['pos'].value, 'lolwut')
                eq_(r.args['nonpos'].value, 'default')
                eq_(len(result), 1) # Not 2

            def positional_args_can_still_be_given_as_flags(self):
                # AKA "positional args can come anywhere in the context"
                pos1 = Argument('pos1', positional=True)
                pos2 = Argument('pos2', positional=True)
                nonpos = Argument('nonpos', positional=False, default='lol')
                mytask = Context('mytask', args=[pos1, pos2, nonpos])
                eq_(mytask.positional_args, [pos1, pos2])
                r = Parser([mytask]).parse_argv([
                    'mytask',
                    '--nonpos', 'wut',
                    '--pos2', 'pos2val',
                    'pos1val',
                ])[0]
                eq_(r.args['pos1'].value, 'pos1val')
                eq_(r.args['pos2'].value, 'pos2val')
                eq_(r.args['nonpos'].value, 'wut')

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
            r = Parser([c]).parse_argv(['mytask', '--foo', '--bar'])
            a = r[0].args
            eq_(a.foo.value, True)
            eq_(a.bar.value, True)

    class optional_arg_values:
        def setup(self):
            self.parser = self._parser()

        def _parser(self, arguments=None):
            if arguments is None:
                arguments = (
                    Argument(
                        names=('foo', 'f'),
                        optional=True,
                        default='mydefault'
                    ),
                )
            self.context = Context('mytask', args=arguments)
            return Parser([self.context])

        def _parse(self, argstr, parser=None):
            parser = parser or self.parser
            return parser.parse_argv(['mytask'] + argstr.split())

        def _expect(self, argstr, expected, parser=None):
            result = self._parse(argstr, parser)
            eq_(result[0].args.foo.value, expected)

        def no_value_becomes_True_not_default_value(self):
            self._expect('--foo', True)
            self._expect('-f', True)

        def value_given_gets_preserved_normally(self):
            for argstr in (
                '--foo whatever',
                '--foo=whatever',
                '-f whatever',
                '-f=whatever',
            ):
                self._expect(argstr, 'whatever')

        def not_given_at_all_uses_default_value(self):
            self._expect('', 'mydefault')

        class ambiguity_sanity_checks:
            def _test_for_ambiguity(self, invoke, parser=None):
                msg = "is ambiguous"
                try:
                    self._parse(invoke, parser or self.parser)
                # Expected result
                except ParseError as e:
                    assert msg in str(e)
                # No exception occurred at all? Bollocks.
                else:
                    assert False
                # Any other exceptions will naturally cause failure here.

            def unfilled_posargs(self):
                p = self._parser((
                    Argument('foo', optional=True),
                    Argument('bar', positional=True)
                ))
                self._test_for_ambiguity("--foo uhoh", p)

            def flaglike_value(self):
                self._test_for_ambiguity("--foo --bar")

            def no_ambiguity_with_flaglike_value_if_option_val_was_given(self):
                p = self._parser((
                    Argument('foo', optional=True),
                    Argument('bar', kind=bool)
                ))
                # This should NOT raise a ParseError.
                result = self._parse("--foo hello --bar", p)
                eq_(result[0].args['foo'].value, 'hello')
                eq_(result[0].args['bar'].value, True)

            def actual_other_flag(self):
                self._parser((
                    Argument('foo', optional=True),
                    Argument('bar')
                ))
                self._test_for_ambiguity("--foo --bar")

            def task_name(self):
                # mytask --foo myothertask
                c1 = Context('mytask', args=(Argument('foo', optional=True),))
                c2 = Context('othertask')
                p = Parser([c1, c2])
                self._test_for_ambiguity("--foo othertask", p)

    class task_repetition:
        def is_happy_to_handle_same_task_multiple_times(self):
            task1 = Context('mytask')
            result = Parser((task1,)).parse_argv(['mytask', 'mytask'])
            eq_(len(result), 2)
            [eq_(x.name, 'mytask') for x in result]

        def task_args_work_correctly(self):
            task1 = Context('mytask', args=(Argument('meh'),))
            result = Parser((task1,)).parse_argv(
                ['mytask', '--meh', 'mehval1', 'mytask', '--meh', 'mehval2']
            )
            eq_(result[0].args.meh.value, 'mehval1')
            eq_(result[1].args.meh.value, 'mehval2')

    class per_task_core_flags:
        class help_:
            def task_has_no_help_shows_per_task_help(self):
                task1 = Context('mytask')
                init = Context(args=[Argument('help', optional=True)])
                parser = Parser(initial=init, contexts=[task1])
                result = parser.parse_argv(['mytask', '--help'])
                eq_(len(result), 2)
                eq_(result[0].args.help.value, 'mytask')
                ok_('help' not in result[1].args)

            # TODO: ideally we want an explosion, but for now, overriding
            # happens naturally and is not the worst thing ever
            def per_task_flag_wins_over_core_flag(self):
                task1 = Context('mytask', args=[Argument('help')])
                init = Context(args=[Argument('help', optional=True)])
                parser = Parser(initial=init, contexts=[task1])
                result = parser.parse_argv(['mytask', '--help', 'foo'])
                eq_(result[1].args.help.value, 'foo')

            def task_has_no_h_shortflag_shows_per_task_help(self):
                task1 = Context('mytask')
                arg = Argument(names=('help', 'h'), optional=True)
                init = Context(args=[arg])
                parser = Parser(initial=init, contexts=[task1])
                result = parser.parse_argv(['mytask', '-h'])
                eq_(len(result), 2)
                eq_(result[0].args.help.value, 'mytask')
                ok_('help' not in result[1].args)

            def task_has_h_shortflag_throws_error(self):
                # def mytask(c, height):
                # inv mytask -h
                skip()

        class other_core_flags_do_not_work_in_task_contexts:
            # NOTE: only doing a subset here for sanity tests
            def list_(self):
                skip()

            def no_dedupe(self):
                skip()

        # TODO: can define what core flags work as per-task flags, somehow?
        # I.e. how to implement --roles/--hosts in fab 2?


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
