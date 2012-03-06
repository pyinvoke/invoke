import os
import sys


class Loader(object):
    pass


class ModuleImporter(object):
    def __init__(self, path):
        self.parent_directory = os.path.dirname(os.path.abspath(path))
        self.module_name = os.path.splitext(os.path.basename(path))[0]

    def lol(self):
        """
        Import ``path`` as a Python module and create a Collection from it.
        """
        # TODO: copy over rest of path munging from fabric.main
        if self.parent_directory not in sys.path:
            sys.path.insert(0, self.parent_directory)
        return __import__(self.module_name)
