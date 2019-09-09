from invoke import termcolor
from io import StringIO


class FakeTTY(StringIO):
    def isatty(self):
        return True


def test_sticky_colors():
    first_coloriser_a = termcolor.sticky_coloriser("a", color_choice=[39])
    second_coloriser_a = termcolor.sticky_coloriser("a", color_choice=[39])
    assert first_coloriser_a is second_coloriser_a

    first_coloriser_b = termcolor.sticky_coloriser("b", color_choice=[39])
    second_coloriser_b = termcolor.sticky_coloriser("b", color_choice=[39])
    assert first_coloriser_b is second_coloriser_b
    assert first_coloriser_b is not first_coloriser_a


def test_tty_output():
    faketty = FakeTTY()
    output = termcolor.white("hello", stream=faketty)
    assert output == "\x1b[0;37mhello\x1b[0m"


def test_no_tty_output():
    output = termcolor.white("hello", stream=StringIO())
    assert output == "hello"
