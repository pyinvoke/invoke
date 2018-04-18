from invoke.util import helpline


class util:
    class helpline:
        def is_empty_string_if_no_docstring(self):
            def foo(c):
                pass
            assert helpline(foo) == ""

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
