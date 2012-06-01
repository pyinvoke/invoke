from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument


class Argument_(Spec):
    class init:
        "__init__"
        def may_take_names_list(self):
            names = ('--foo', '-f')
            a = Argument(names=names)
            # herp a derp
            for name in names:
                assert name in a.names

        def may_take_name_arg(self):
            assert '-b' in Argument(name='-b').names

        @raises(TypeError)
        def must_get_at_least_one_name(self):
            Argument()

    class kind_kwarg:
        "'kind' kwarg"

        def is_optional(self):
            Argument(name='a')
            Argument(name='b', kind=int)

        def defaults_to_bool(self):
            eq_(Argument('a').kind, bool)

        def non_bool_implies_value_needed(self):
            assert Argument(name='a', kind=int).takes_value

        def bool_implies_no_value_needed(self):
            assert not Argument(name='a', kind=bool).takes_value

        @raises(ValueError)
        def may_validate_on_set(self):
            Argument('a', kind=int).value = 'five'

    class names:
        def returns_tuple_of_all_names(self):
            eq_(Argument(names=('--foo', '-b')).names, ('--foo', '-b'))
            eq_(Argument(name='--foo').names, ('--foo',))

    class takes_value:
        def False_for_basic_args(self):
            assert not Argument(name='a').takes_value

        def True_if_kind_is_set(self):
            assert Argument(name='-b', kind=str).takes_value

    class value_set:
        "value="
        def available_as_dot_raw_value(self):
            "available as .raw_value"
            a = Argument('a')
            a.value = 'foo'
            eq_(a.raw_value, 'foo')

        def untransformed_appears_as_dot_value(self):
            "untransformed, appears as .value"
            a = Argument('a', kind=str)
            a.value = 'foo'
            eq_(a.value, 'foo')

        def transformed_appears_as_dot_value_with_original_as_raw_value(self):
            "transformed, modified value is .value, original is .raw_value"
            a = Argument('a', kind=int)
            a.value = '5'
            eq_(a.value, 5)
            eq_(a.raw_value, '5')

    class value:
        def returns_default_if_not_set(self):
            a = Argument('a', default=25)
            eq_(a.value, 25)

    class raw_value:
        def is_None_when_no_value_was_actually_seen(self):
            a = Argument('a', kind=int)
            eq_(a.raw_value, None)
