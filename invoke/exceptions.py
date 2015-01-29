"""
Custom exception classes.

These vary in use case from "we needed a specific data structure layout in
exceptions used for message-passing" to simply "we needed to express an error
condition in a way easily told apart from other, truly unexpected errors".
"""

class CollectionNotFound(Exception):
    def __init__(self, name, start):
        self.name = name
        self.start = start


class Failure(Exception):
    """
    Exception subclass representing failure of a command execution.

    It exhibits a ``result`` attribute containing the related `.Result` object,
    whose attributes may be inspected to determine why the command failed.
    """
    def __init__(self, result):
        self.result = result

    def __str__(self):
        return """Command execution failure!

Exit code: {0}

Stderr:

{1}

""".format(self.result.exited, self.result.stderr)

    def __repr__(self):
        return str(self)


class ParseError(Exception):
    def __init__(self, msg, context=None):
        super(ParseError, self).__init__(msg)
        self.context = context


class Exit(Exception):
    """
    Simple stand-in for SystemExit that lets us gracefully exit.

    Removes lots of scattered sys.exit calls, improves testability.
    """
    def __init__(self, code=0):
        self.code = code


class PlatformError(Exception):
    """
    Raised when an illegal operation occurs for the current platform.

    E.g. Windows users trying to import the ``pexpect`` module.

    Typically used to present a clearer error message to the user.
    """
    pass


class AmbiguousEnvVar(Exception):
    """
    Raised when loading env var config keys has an ambiguous target.
    """
    pass


class UncastableEnvVar(Exception):
    """
    Raised on attempted env var loads whose default values are too rich.

    E.g. trying to stuff ``MY_VAR="foo"`` into ``{'my_var': ['uh', 'oh']}``
    doesn't make any sense until/if we implement some sort of transform option.
    """
    pass


class UnknownFileType(Exception):
    """
    A config file of an unknown type was specified and cannot be loaded.
    """
    pass
