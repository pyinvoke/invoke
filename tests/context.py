import copy

from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument, Context


class Context_(Spec):
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

        def can_take_kwargs(self):
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

        def turns_single_character_names_into_short_flags(self):
            self.c.add_arg('f')
            assert '-f' in self.c.flags
            assert '--f' not in self.c.flags

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
            self.ctx = Context(args=(
                Argument('foo'),
                Argument('bar', help="bar the baz")
            ))

        def no_helpstr(self):
            eq_(
                self.help_for('foo'),
                "--foo=STRING, -f STRING"
            )

        def with_helpstr(self):
            eq_(
                self.help_for('bar'),
                "--bar=STRING, -b STRING        bar the baz"
            )

    class help_lines:
        def returns_list_of_help_output_strings(self):
            # Walks own list of flags/args, ensures resulting map to help_for()
            skip()

        def sorts_alphabetically_by_shortflag_first(self):
            # Where shortflags exist, they take precedence
            skip()

        def sorts_alphabetically_by_longflag_when_no_shortflag(self):
            # Where no shortflag, sorts by longflag
            skip()

        def sorts_heterogenous_help_output_with_longflag_only_options_first(self):
            # When both types of options exist, long flag only options come
            # first.
            # E.g.:
            #   --alpha
            #   --beta
            #   -a, --aaaagh
            #   -b, --bah
            #   -c
            skip()
