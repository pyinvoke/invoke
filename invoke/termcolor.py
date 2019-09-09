"""
This module contains simple functions to colorise terminal output.

The support is limited and only supports 16-color ANSI on *nix platforms.

Output can also be be completely disabled by setting the environment variable
``INVOKE_DISABLE_COLORS``


Example usage::

    >>> from invoke.termcolor import green
    >>> print(green('Hello World!'))
    >>> print(green('Hello World!', bold=True))
"""
from os import getenv
from random import choice
from sys import platform, stdout
from typing import Callable, Dict, List, Optional
from typing.io import IO

#: If this is set to "True", no color output will be enabled
DISABLE_COLORS = bool(getenv("INVOKE_DISABLE_COLORS", False))

#: This collection keeps track of already assigned colorisers, so the same can
#: be used repeatedly for the same key
KEYED_COLORISERS = {}  # type: Dict[str, Callable[..., str]]


def color_wrapper(color_code):
    # type: (int) -> Callable[..., str]
    """
    Creates a wrapper function for colorised text.

    :param color_code: The ANSI color code

    The returned function takes one mandatory and two optional arguments. The
    signature is::

        def coloriser(
            text: str,
            bold: bool = False,
            stream: IO = stdout
        ) -> str: ...

    Example::

        >>> mywrapper = color_wrapper(37)
        >>> mywrapper('<thetext>')
        '\033[0;37m<thetext>\033[0m'
        >>> mywrapper('<thetext>', bold=True)
        '\033[1;37m<thetext>\033[0m'
    """

    def coloriser(text, bold=False, stream=stdout):
        # type: (str, bool, IO) -> str
        """
        Returns *text* wrapped with color information (including a "reset" to
        defaults at the end of the string). If *stream* is not a valid TTY, the
        text is returned unmodified.

        :param text: The text to be colorised
        :param bold: Whether to use the "bold/bright" variant of the color
            or not.
        :param stream: The stream to which the text should be printed. This is
            used to determine if we should drop the escape-codes (and print
            simple black-and-white text) or not.
        """
        if (
            DISABLE_COLORS
            or not stream.isatty()
            or platform == "win32"
        ):
            # We only want color output on a TTY and on a platform which
            # supports ANSI color codes. For all other cases we just return the
            # text unmodified.
            return text

        modifier = 1 if bold else 0
        return "\033[%d;%dm%s\033[0m" % (modifier, color_code, text)

    return coloriser


def sticky_coloriser(key, color_choice=None):
    # type: (str, Optional[List[int]]) -> Callable[..., str]
    """
    Returns a random color for a given key. It guarantees that the same
    coloriser is returned for the same key.

    :param key: The key by which to identify the coloriser
    :param color_choice: A collection of possible ANSI color codes. If left to
        "None", all supported color other than white and black are used
    """
    if key not in KEYED_COLORISERS:
        colors = color_choice or range(31, 37)
        new_coloriser = color_wrapper(choice(colors))
        KEYED_COLORISERS[key] = new_coloriser
    return KEYED_COLORISERS[key]


black = color_wrapper(30)
red = color_wrapper(31)
green = color_wrapper(32)
yellow = color_wrapper(33)
blue = color_wrapper(34)
magenta = color_wrapper(35)
cyan = color_wrapper(36)
white = color_wrapper(37)
