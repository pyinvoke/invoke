from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument, Context


class Context_(Spec):
    def may_have_a_name(self):
        skip()

    def may_have_aliases(self):
        skip()

    class add_arg:
        def can_take_Argument_instance(self):
            c = Context()
            a = Argument(names=('foo',))
            c.add_arg(a)
            assert c.get_arg('foo') is a

        def can_take_kwargs(self):
            c = Context()
            c.add_arg(names=('foo', 'bar'))
            assert c.get_arg('foo').answers_to('bar')

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
