import os
import sys
import imp

from .collection import Collection
from .exceptions import CollectionNotFound
from .tasks import Task


class Loader(object):
    def __init__(self, root=None):
        """
        Creates a loader object with search root directory of ``root``.

        If not given, ``root`` defaults to ``os.getcwd``.
        """
        self.root = root or os.getcwd()

    def get_parent_directory(self, path):
        """Return the parent directory of the given ``path``"""
        return os.path.abspath(os.path.join(path, '..'))

    def update_path(self, path, root=None):
        """
        Ensures ``root`` is added to a copy of the given ``path`` iterable.

        It is up to the caller to assign the return value to e.g. ``sys.path``.
        """
        parent = os.path.abspath(root or self.root)
        our_path = path[:]
        # If we want to auto-strip .py:
        # os.path.splitext(os.path.basename(name))[0]
        our_path.insert(0, parent)
        return our_path

    def find_collection(self, name):
        """
        Seek towards FS root from self.root for Python module ``name``.

        Returns a tuple suitable for use in ``imp.load_module``.
        """
        # Add root to system path
        # TODO: decide correct behavior re: leaving sys.path modified.
        # imp.find_module can take an arbitrary path, after all. But users may
        # find it useful to have local-to-tasks-module Python code on the
        # import path.
        root = self.root
        sys.path, original_path = self.update_path(sys.path), sys.path
        try:
            while True:
                try:
                    return tuple(
                        [name] + list(imp.find_module(name, sys.path))
                    )
                except ImportError:
                    previous_root = root
                    root = self.get_parent_directory(previous_root)
                    # we've reached the root of the FS and haven't found the
                    # collection
                    if root == previous_root:
                        raise

                    sys.path = self.update_path(original_path, root=root)

        # ImportErrors raised by imp.find_module indicate the requested module
        # does not exist, not that it exists & couldn't be imported (which is
        # typically what ImportError means)
        except ImportError:
            raise CollectionNotFound(name=name, root=self.root)

    def load_collection(self, name=None):
        """
        Load and return collection named ``name``.

        If not given, looks for a ``"tasks"`` collection by default.
        """
        if name is None:
            # TODO: make this configurable
            name = 'tasks'
        # Import. Errors during import will raise normally.
        module = imp.load_module(*self.find_collection(name))
        return Collection.from_module(module)
