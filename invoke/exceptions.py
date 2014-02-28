class CollectionNotFound(Exception):
    def __init__(self, name, root):
        self.name = name
        self.root = root


class Failure(Exception):
    """
    Exception subclass representing failure of a command execution.

    It exhibits a ``result`` attribute containing the related `Result` object,
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
