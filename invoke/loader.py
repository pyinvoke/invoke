import os
import sys


class Loader(object):
    def __init__(self, collections=None, root=None):
        """
        Stores given ``collections`` list and/or ``root`` path string.

        If either is ``None``, appropriate default values will be substituted.
        """
        self.collections = collections or ['tasks']
        self.root = root or os.getcwd()


class ModuleImporter(object):
    def __init__(self, path):
        self.parent_directory = os.path.dirname(os.path.abspath(path))
        self.module_name = os.path.splitext(os.path.basename(path))[0]

    def load(self):
        """
        Import ``path`` as a Python module and create a Collection from it.
        """
        # TODO: copy over rest of path munging from fabric.main
        if self.parent_directory not in sys.path:
            sys.path.insert(0, self.parent_directory)
        return __import__(self.module_name)
