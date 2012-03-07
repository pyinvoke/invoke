class CollectionNotFound(Exception):
    def __init__(self, name, root, error):
        self.name = name
        self.root = root
        self.error = error
