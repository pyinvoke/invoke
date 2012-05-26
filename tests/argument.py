from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument


class Argument_(Spec):
    def may_take_names_list(self):
        names = ('--foo', '-f')
        a = Argument(names=names)
        # herp a derp
        for name in names:
            assert name in a.names

    def may_take_name_arg(self):
        assert '-b' in Argument(name='-b').names

    @raises(TypeError)
    def must_have_at_least_one_name(self):
        Argument()

    def defaults_to_not_needing_a_value(self):
        assert not Argument(name='a').needs_value

    def may_specify_value_factory(self):
        assert Argument(name='a', value=str).needs_value

    class names:
        def returns_tuple_of_all_names(self):
            eq_(Argument(names=('--foo', '-b')).names, ('--foo', '-b'))
            eq_(Argument(name='--foo').names, ('--foo',))

    class needs_value:
        def returns_True_if_this_argument_needs_a_value(self):
            assert Argument(name='-b', value=str).needs_value

        def returns_False_if_it_does_not_need_a_value(self):
            assert not Argument(name='-b', value=None).needs_value
