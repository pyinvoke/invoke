class CollectionNotFound(Exception):
    def __init__(self, name, root, error):
        self.name = name
        self.root = root
        self.error = error


class Failure(Exception):
    """
    Exception subclass representing failure of a command execution.

    It exhibits a ``result`` attribute containing the related `Result` object,
    whose attributes may be inspected to determine why the command failed.
    """
    def __init__(self, result):
        self.result = result
