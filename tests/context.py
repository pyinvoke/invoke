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

        def turns_single_character_names_into_short_flags(self):
            self.c.add_arg('f')
            assert '-f' in self.c.flags
            assert '--f' not in self.c.flags

        def does_not_add_positional_arg_to_flags(self):
            self.c.add_arg(name='pos', positional=True)
            assert '--pos' not in self.c.flags
            assert '-p' not in self.c.flags

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
