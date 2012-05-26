from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument, Context


class Context_(Spec):
    def may_have_a_name(self):
        c = Context(name='taskname')
        eq_(c.name, 'taskname')

    def may_have_aliases(self):
        c = Context(name='realname', aliases=('othername', 'yup'))
        assert 'othername' in c.aliases

    class add_arg:
        def can_take_Argument_instance(self):
            c = Context()
            a = Argument(names=('foo',))
            c.add_arg(a)
            assert c.get_arg('foo') is a

        def can_take_name_arg(self):
            c = Context()
            c.add_arg('foo')
            assert c.has_arg('foo')

        def can_take_kwargs(self):
            c = Context()
            c.add_arg(names=('foo', 'bar'))
            assert c.has_arg('foo') and c.has_arg('bar')

        @raises(ValueError)
        def raises_ValueError_on_duplicate(self):
            c = Context()
            c.add_arg(names=('foo', 'bar'))
            c.add_arg(name='bar')

    class has_arg:
        def returns_True_if_flag_is_valid_arg(self):
            c = Context()
            c.add_arg(Argument(names=('foo',)))
            eq_(c.has_arg('foo'), True)

    class get_arg:
        def returns_Argument_for_given_name(self):
            c = Context()
            a = Argument(name='foo')
            c.add_arg(a)
            assert c.get_arg('foo') is a
