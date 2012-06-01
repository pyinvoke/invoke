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
        def can_take_Argument_instance(self):
            c = Context()
            a = Argument(names=('foo',))
            c.add_arg(a)
            assert c.args['foo'] is a

        def can_take_name_arg(self):
            c = Context()
            c.add_arg('foo')
            assert 'foo' in c.args

        def can_take_kwargs(self):
            c = Context()
            c.add_arg(names=('foo', 'bar'))
            assert 'foo' in c.args and 'bar' in c.args

        @raises(ValueError)
        def raises_ValueError_on_duplicate(self):
            c = Context()
            c.add_arg(names=('foo', 'bar'))
            c.add_arg(name='bar')

    class deepcopy:
        "__deepcopy__"
        def returns_correct_copy(self):
            orig = Context(name='foo', aliases=('bar',))
            new = copy.deepcopy(orig)
            assert new is not orig
            eq_(new.name, 'foo')
            assert 'bar' in new.aliases

        def includes_arguments(self):
            arg = Argument('--boolean')
            orig = Context(name='mytask', args=(arg,))
            new = copy.deepcopy(orig)
            eq_(len(new.args), 1)
            assert new.args['--boolean'] is not arg

        def modifications_to_copied_arguments_do_not_touch_originals(self):
            arg = Argument('--boolean')
            orig = Context('mytask', args=(arg,))
            new = copy.deepcopy(orig)
            new_arg = new.args['--boolean']
            new_arg.value = True
            assert new_arg.value
            assert not arg.value
