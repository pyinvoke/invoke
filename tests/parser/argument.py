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

        def default_arg_is_name_not_names(self):
            assert 'b' in Argument('b').names

        def can_declare_positional(self):
            eq_(Argument(name='foo', positional=True).positional, True)

        def positional_is_False_by_default(self):
            eq_(Argument(name='foo').positional, False)

        def can_set_attr_name_to_control_name_attr(self):
            a = Argument('foo', attr_name='bar')
            eq_(a.name, 'bar') # not 'foo'

    class string:
        "__str__"

        def shows_useful_info(self):
            eq_(
                str(Argument(names=('name', 'nick1', 'nick2'))),
                "<Argument: %s (%s)>" % ('name', 'nick1, nick2')
            )

        def does_not_show_nickname_parens_if_no_nicknames(self):
            eq_(
                str(Argument('name')),
                "<Argument: name>"
            )

        def shows_positionalness(self):
            eq_(
                str(Argument('name', positional=True)),
                "<Argument: name*>"
            )

    class repr:
        "__repr__"

        def just_aliases_dunder_str(self):
            a = Argument(names=('name', 'name2'))
            eq_(str(a), repr(a))

    class kind_kwarg:
        "'kind' kwarg"

        def is_optional(self):
            Argument(name='a')
            Argument(name='b', kind=int)

        def defaults_to_str(self):
            eq_(Argument('a').kind, str)

        def non_bool_implies_value_needed(self):
            assert Argument(name='a', kind=int).takes_value

        def bool_implies_no_value_needed(self):
            assert not Argument(name='a', kind=bool).takes_value

        def bool_implies_default_False_not_None(self):
            # Right now, parsing a bool flag not given results in None
            # TODO: may want more nuance here -- False when a --no-XXX flag is
            # given, True if --XXX, None if not seen?
            # Only makes sense if we add automatic --no-XXX stuff (think
            # ./configure)
            skip()

        @raises(ValueError)
        def may_validate_on_set(self):
            Argument('a', kind=int).value = 'five'

    class names:
        def returns_tuple_of_all_names(self):
            eq_(Argument(names=('--foo', '-b')).names, ('--foo', '-b'))
            eq_(Argument(name='--foo').names, ('--foo',))

        def is_normalized_to_a_tuple(self):
            ok_(isinstance(Argument(names=('a', 'b')).names, tuple))

    class name:
        def returns_first_name(self):
            eq_(Argument(names=('a', 'b')).name, 'a')

    class nicknames:
        def returns_rest_of_names(self):
            eq_(Argument(names=('a', 'b')).nicknames, ('b',))

    class takes_value:
        def True_by_default(self):
            assert Argument(name='a').takes_value

        def False_if_kind_is_bool(self):
            assert not Argument(name='-b', kind=bool).takes_value

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

    class set_value:
        def casts_by_default(self):
            a = Argument('a', kind=int)
            a.set_value('5')
            eq_(a.value, 5)

        def allows_setting_value_without_casting(self):
            a = Argument('a', kind=int)
            a.set_value('5', cast=False)
            eq_(a.value, '5')
