import copy

from spec import Spec, eq_, skip, raises

from invoke.parser import Argument, Context
from invoke.tasks import task
from invoke.collection import Collection


class Context_(Spec):
    "ParserContext" # meh
    def may_have_a_name(self):
        c = Context(name='taskname')
        eq_(c.name, 'taskname')

    def may_have_aliases(self):
        c = Context(name='realname', aliases=('othername', 'yup'))
        assert 'othername' in c.aliases

    def may_give_arg_list_at_init_time(self):
        a1 = Argument('foo')
        a2 = Argument('bar')
        c = Context(name='name', args=(a1, a2))
        assert c.args['foo'] is a1

    # TODO: reconcile this sort of test organization with the .flags oriented
    # tests within 'add_arg'.  Some of this behavior is technically driven by
    # add_arg.
    class args:
        def setup(self):
            self.c = Context(args=(
                Argument('foo'),
                Argument(names=('bar', 'biz')),
                Argument('baz', attr_name='wat'),
            ))

        def exposed_as_dict(self):
            assert 'foo' in self.c.args.keys()

        def exposed_as_Lexicon(self):
            eq_(self.c.args.bar, self.c.args['bar'])

        def args_dict_includes_all_arg_names(self):
            for x in ('foo', 'bar', 'biz'):
                assert x in self.c.args

        def argument_attr_names_appear_in_args_but_not_flags(self):
            # Both appear as "Python-facing" args
            for x in ('baz', 'wat'):
                assert x in self.c.args
            # But attr_name is for Python access only and isn't shown to the
            # parser.
            assert 'wat' not in self.c.flags

    class add_arg:
        def setup(self):
            self.c = Context()

        def can_take_Argument_instance(self):
            a = Argument(names=('foo',))
            self.c.add_arg(a)
            assert self.c.args['foo'] is a

        def can_take_name_arg(self):
            self.c.add_arg('foo')
            assert 'foo' in self.c.args

        def can_take_kwargs_for_single_Argument(self):
            self.c.add_arg(names=('foo', 'bar'))
            assert 'foo' in self.c.args and 'bar' in self.c.args

        @raises(ValueError)
        def raises_ValueError_on_duplicate(self):
            self.c.add_arg(names=('foo', 'bar'))
            self.c.add_arg(name='bar')

        def adds_flaglike_name_to_dot_flags(self):
            "adds flaglike name to .flags"
            self.c.add_arg('foo')
            assert '--foo' in self.c.flags

        def adds_all_names_to_dot_flags(self):
            "adds all names to .flags"
            self.c.add_arg(names=('foo', 'bar'))
            assert '--foo' in self.c.flags
            assert '--bar' in self.c.flags

        def adds_true_bools_to_inverse_flags(self):
            self.c.add_arg(name='myflag', default=True, kind=bool)
            assert '--myflag' in self.c.flags
            assert '--no-myflag' in self.c.inverse_flags
            eq_(self.c.inverse_flags['--no-myflag'], '--myflag')

        def inverse_flags_works_right_with_task_driven_underscored_names(self):
            # Use a Task here instead of creating a raw argument, we're partly
            # testing Task.get_arguments()' transform of underscored names
            # here. Yes that makes this an integration test, but it's nice to
            # test it here at this level & not just in cli tests.
            @task
            def mytask(ctx, underscored_option=True):
                pass
            self.c.add_arg(mytask.get_arguments()[0])
            eq_(
                self.c.inverse_flags['--no-underscored-option'],
                '--underscored-option'
            )

        def turns_single_character_names_into_short_flags(self):
            self.c.add_arg('f')
            assert '-f' in self.c.flags
            assert '--f' not in self.c.flags

        def adds_positional_args_to_positional_args(self):
            self.c.add_arg(name='pos', positional=True)
            eq_(self.c.positional_args[0].name, 'pos')

        def positional_args_empty_when_none_given(self):
            eq_(len(self.c.positional_args), 0)

        def positional_args_filled_in_order(self):
            self.c.add_arg(name='pos1', positional=True)
            eq_(self.c.positional_args[0].name, 'pos1')
            self.c.add_arg(name='abc', positional=True)
            eq_(self.c.positional_args[1].name, 'abc')

        def positional_arg_modifications_affect_args_copy(self):
            self.c.add_arg(name='hrm', positional=True)
            eq_(self.c.args['hrm'].value, self.c.positional_args[0].value)
            self.c.positional_args[0].value = 17
            eq_(self.c.args['hrm'].value, self.c.positional_args[0].value)

    class deepcopy:
        "__deepcopy__"
        def setup(self):
            self.arg = Argument('--boolean')
            self.orig = Context(
                name='mytask',
                args=(self.arg,),
                aliases=('othername',)
            )
            self.new = copy.deepcopy(self.orig)

        def returns_correct_copy(self):
            assert self.new is not self.orig
            eq_(self.new.name, 'mytask')
            assert 'othername' in self.new.aliases

        def includes_arguments(self):
            eq_(len(self.new.args), 1)
            assert self.new.args['--boolean'] is not self.arg

        def modifications_to_copied_arguments_do_not_touch_originals(self):
            new_arg = self.new.args['--boolean']
            new_arg.value = True
            assert new_arg.value
            assert not self.arg.value

    class help_for:
        def setup(self):
            # Normal, non-task/collection related Context
            self.vanilla = Context(args=(
                Argument('foo'),
                Argument('bar', help="bar the baz")
            ))
            # Task/Collection generated Context
            # (will expose flags n such)
            @task(help={'otherarg': 'other help'}, optional=['optval'])
            def mytask(ctx, myarg, otherarg, optval):
                pass
            col = Collection(mytask)
            self.tasked = col.to_contexts()[0]

        @raises(ValueError)
        def raises_ValueError_for_non_flag_values(self):
            self.vanilla.help_for('foo')

        def vanilla_no_helpstr(self):
            eq_(
                self.vanilla.help_for('--foo'),
                ("--foo=STRING", "")
            )

        def vanilla_with_helpstr(self):
            eq_(
                self.vanilla.help_for('--bar'),
                ("--bar=STRING", "bar the baz")
            )

        def task_driven_with_helpstr(self):
            eq_(
                self.tasked.help_for('--otherarg'),
                ("-o STRING, --otherarg=STRING", "other help")
            )

        # Yes, the next 3 tests are identical in form, but technically they
        # test different behaviors. HERPIN' AN' DERPIN'
        def task_driven_no_helpstr(self):
            eq_(
                self.tasked.help_for('--myarg'),
                ("-m STRING, --myarg=STRING", "")
            )

        def short_form_before_long_form(self):
            eq_(
                self.tasked.help_for('--myarg'),
                ("-m STRING, --myarg=STRING", "")
            )

        def equals_sign_for_long_form_only(self):
            eq_(
                self.tasked.help_for('--myarg'),
                ("-m STRING, --myarg=STRING", "")
            )

        def kind_to_placeholder_map(self):
            # str=STRING, int=INT, etc etc
            skip()

        def shortflag_inputs_work_too(self):
            eq_(self.tasked.help_for('-m'), self.tasked.help_for('--myarg'))

        def optional_values_use_brackets(self):
            eq_(
                self.tasked.help_for('--optval'),
                ("-p [STRING], --optval[=STRING]", "")
            )

        def underscored_args(self):
            c = Context(args=(Argument('i_have_underscores', help='yup'),))
            eq_(
                c.help_for('--i-have-underscores'),
                ('--i-have-underscores=STRING', 'yup')
            )

        def true_default_args(self):
            c = Context(args=(Argument('truthy', kind=bool, default=True),))
            eq_(c.help_for('--truthy'), ('--[no-]truthy', ''))

    class help_tuples:
        def returns_list_of_help_tuples(self):
            # Walks own list of flags/args, ensures resulting map to help_for()
            # TODO: consider redoing help_for to be more flexible on input --
            # arg value or flag; or even Argument objects. ?
            @task(help={'otherarg': 'other help'})
            def mytask(ctx, myarg, otherarg):
                pass
            c = Collection(mytask).to_contexts()[0]
            eq_(
                c.help_tuples(),
                [c.help_for('--myarg'), c.help_for('--otherarg')]
            )

        def _assert_order(self, name_tuples, expected_flag_order):
            ctx = Context(args=[Argument(names=x) for x in name_tuples])
            return eq_(
                ctx.help_tuples(),
                [ctx.help_for(x) for x in expected_flag_order]
            )

        def sorts_alphabetically_by_shortflag_first(self):
            # Where shortflags exist, they take precedence
            self._assert_order(
                [('zarg', 'a'), ('arg', 'z')],
                ['--zarg', '--arg']
            )

        def case_ignored_during_sorting(self):
            self._assert_order(
                [('a',), ('B',)],
                # In raw cmp() uppercase would come before lowercase,
                # and we'd get ['-B', '-a']
                ['-a', '-B']
            )

        def lowercase_wins_when_values_identical_otherwise(self):
            self._assert_order(
                [('V',), ('v',)],
                ['-v', '-V']
            )

        def sorts_alphabetically_by_longflag_when_no_shortflag(self):
            # Where no shortflag, sorts by longflag
            self._assert_order(
                [('otherarg',), ('longarg',)],
                ['--longarg', '--otherarg']
            )

        def sorts_heterogenous_help_output_with_longflag_only_options_first(self): # noqa
            # When both of the above mix, long-flag-only options come first.
            # E.g.:
            #   --alpha
            #   --beta
            #   -a, --aaaagh
            #   -b, --bah
            #   -c
            self._assert_order(
                [('c',), ('a', 'aaagh'), ('b', 'bah'), ('beta',), ('alpha',)],
                ['--alpha', '--beta', '-a', '-b', '-c']
            )

        def mixed_corelike_options(self):
            self._assert_order(
                [('V', 'version'), ('c', 'collection'), ('h', 'help'),
                    ('l', 'list'), ('r', 'root')],
                ['-c', '-h', '-l', '-r', '-V']
            )

    class needs_positional_arg:
        def represents_whether_all_positional_args_have_values(self):
            c = Context(name='foo', args=(
                Argument('arg1', positional=True),
                Argument('arg2', positional=False),
                Argument('arg3', positional=True),
            ))
            eq_(c.needs_positional_arg, True)
            c.positional_args[0].value = 'wat'
            eq_(c.needs_positional_arg, True)
            c.positional_args[1].value = 'hrm'
            eq_(c.needs_positional_arg, False)

    class str:
        "__str__"
        def with_no_args_output_is_simple(self):
            eq_(str(Context('foo')), "<parser/Context 'foo'>")

        def args_show_as_repr(self):
            eq_(
                str(Context('bar', args=[Argument('arg1')])),
                "<parser/Context 'bar': {'arg1': <Argument: arg1>}>"
            )
