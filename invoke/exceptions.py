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


class ParseError(Exception):
    def __init__(self, msg, context=None):
        super(ParseError, self).__init__(msg)
        self.context = context
