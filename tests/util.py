from invoke.util import helpline


class util:
    class helpline:
        def is_None_if_no_docstring(self):
            def foo(c):
                pass

            assert helpline(foo) is None

        def is_entire_thing_if_docstring_one_liner(self):
            def foo(c):
                "foo!"
                pass

            assert helpline(foo) == "foo!"

        def left_strips_newline_bearing_one_liners(self):
            def foo(c):
                """
                foo!
                """
                pass

            assert helpline(foo) == "foo!"

        def is_first_line_in_multiline_docstrings(self):
            def foo(c):
                """
                foo?

                foo!
                """
                pass

            assert helpline(foo) == "foo?"

        def is_None_if_docstring_matches_object_type(self):
            # I.e. we don't want a docstring that is coming from the class
            # instead of the instance.
            class Foo(object):
                "I am Foo"
                pass

            foo = Foo()
            assert helpline(foo) is None

        def instance_attached_docstring_is_still_displayed(self):
            # This is actually a property of regular object semantics, but
            # whatever, why not have a test for it.
            class Foo(object):
                "I am Foo"
                pass

            foo = Foo()
            foo.__doc__ = "I am foo"
            assert helpline(foo) == "I am foo"
