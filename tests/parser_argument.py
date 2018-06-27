from pytest import skip, raises

from invoke.parser import Argument


class Argument_:
    class init:
        "__init__"

        def may_take_names_list(self):
            names = ("--foo", "-f")
            a = Argument(names=names)
            # herp a derp
            for name in names:
                assert name in a.names

        def may_take_name_arg(self):
            assert "-b" in Argument(name="-b").names

        def must_get_at_least_one_name(self):
            with raises(TypeError):
                Argument()

        def default_arg_is_name_not_names(self):
            assert "b" in Argument("b").names

        def can_declare_positional(self):
            assert Argument(name="foo", positional=True).positional is True

        def positional_is_False_by_default(self):
            assert Argument(name="foo").positional is False

        def can_set_attr_name_to_control_name_attr(self):
            a = Argument("foo", attr_name="bar")
            assert a.name == "bar"  # not 'foo'

    class repr:
        "__repr__"

        def shows_useful_info(self):
            arg = Argument(names=("name", "nick1", "nick2"))
            expected = "<Argument: {} ({})>".format("name", "nick1, nick2")
            assert repr(arg) == expected

        def does_not_show_nickname_parens_if_no_nicknames(self):
            assert repr(Argument("name")) == "<Argument: name>"

        def shows_positionalness(self):
            arg = Argument("name", positional=True)
            assert repr(arg) == "<Argument: name *>"

        def shows_optionalness(self):
            arg = Argument("name", optional=True)
            assert repr(arg) == "<Argument: name ?>"

        def positionalness_and_optionalness_stick_together(self):
            # TODO: but do these even make sense on the same argument? For now,
            # best to have a nonsensical test than a missing one...
            arg = Argument("name", optional=True, positional=True)
            assert repr(arg) == "<Argument: name *?>"

        def shows_kind_if_not_str(self):
            assert repr(Argument("age", kind=int)) == "<Argument: age [int]>"

        def all_the_things_together(self):
            arg = Argument(
                names=("meh", "m"), kind=int, optional=True, positional=True
            )
            assert repr(arg) == "<Argument: meh (m) [int] *?>"

    class kind_kwarg:
        "'kind' kwarg"

        def is_optional(self):
            Argument(name="a")
            Argument(name="b", kind=int)

        def defaults_to_str(self):
            assert Argument("a").kind == str

        def non_bool_implies_value_needed(self):
            assert Argument(name="a", kind=int).takes_value
            assert Argument(name="b", kind=str).takes_value
            assert Argument(name="c", kind=list).takes_value

        def bool_implies_no_value_needed(self):
            assert not Argument(name="a", kind=bool).takes_value

        def bool_implies_default_False_not_None(self):
            # Right now, parsing a bool flag not given results in None
            # TODO: may want more nuance here -- False when a --no-XXX flag is
            # given, True if --XXX, None if not seen?
            # Only makes sense if we add automatic --no-XXX stuff (think
            # ./configure)
            skip()

        def may_validate_on_set(self):
            with raises(ValueError):
                Argument("a", kind=int).value = "five"

        def list_implies_initial_value_of_empty_list(self):
            assert Argument("mylist", kind=list).value == []

    class names:
        def returns_tuple_of_all_names(self):
            assert Argument(names=("--foo", "-b")).names == ("--foo", "-b")
            assert Argument(name="--foo").names == ("--foo",)

        def is_normalized_to_a_tuple(self):
            assert isinstance(Argument(names=("a", "b")).names, tuple)

    class name:
        def returns_first_name(self):
            assert Argument(names=("a", "b")).name == "a"

    class nicknames:
        def returns_rest_of_names(self):
            assert Argument(names=("a", "b")).nicknames == ("b",)

    class takes_value:
        def True_by_default(self):
            assert Argument(name="a").takes_value

        def False_if_kind_is_bool(self):
            assert not Argument(name="-b", kind=bool).takes_value

    class value_set:
        "value="

        def available_as_dot_raw_value(self):
            "available as .raw_value"
            a = Argument("a")
            a.value = "foo"
            assert a.raw_value == "foo"

        def untransformed_appears_as_dot_value(self):
            "untransformed, appears as .value"
            a = Argument("a", kind=str)
            a.value = "foo"
            assert a.value == "foo"

        def transformed_appears_as_dot_value_with_original_as_raw_value(self):
            "transformed, modified value is .value, original is .raw_value"
            a = Argument("a", kind=int)
            a.value = "5"
            assert a.value == 5
            assert a.raw_value == "5"

        def list_kind_triggers_append_instead_of_overwrite(self):
            # TODO: when put this way it makes the API look pretty strange;
            # maybe a sign we should switch to explicit setter methods
            # (selected on kind, perhaps) instead of using an implicit setter
            a = Argument("mylist", kind=list)
            assert a.value == []
            a.value = "val1"
            assert a.value == ["val1"]
            a.value = "val2"
            assert a.value == ["val1", "val2"]

        def incrementable_True_triggers_increment_of_default(self):
            a = Argument("verbose", kind=int, default=0, incrementable=True)
            assert a.value == 0
            # NOTE: parser currently just goes "Argument.takes_value is false?
            # Gonna stuff True/False in there." So this looks pretty silly out
            # of context (as with list-types above.)
            a.value = True
            assert a.value == 1
            for _ in range(4):
                a.value = True
            assert a.value == 5

    class value:
        def returns_default_if_not_set(self):
            a = Argument("a", default=25)
            assert a.value == 25

    class raw_value:
        def is_None_when_no_value_was_actually_seen(self):
            a = Argument("a", kind=int)
            assert a.raw_value is None

    class set_value:
        def casts_by_default(self):
            a = Argument("a", kind=int)
            a.set_value("5")
            assert a.value == 5

        def allows_setting_value_without_casting(self):
            a = Argument("a", kind=int)
            a.set_value("5", cast=False)
            assert a.value == "5"
