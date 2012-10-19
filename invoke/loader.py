import os
import sys

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

    def update_path(self, path):
        """
        Ensures ``self.root`` is added to a copy of the given ``path`` iterable.

        It is up to the caller to assign the return value to e.g. ``sys.path``.
        """
        parent = os.path.abspath(self.root)
        our_path = path[:]
        # If we want to auto-strip .py:
        # os.path.splitext(os.path.basename(name))[0]
        # TODO: copy over rest of path munging from fabric.main
        if parent not in our_path:
            our_path.insert(0, parent)
        return our_path

    def add_to_collection(self, name, collection):
        """
        Load all valid tasks from module ``name``, adding to ``collection``.

        Raises ``CollectionNotFound`` if the module is unable to be imported.
        """
        try:
            module = __import__(name)
            candidates = filter(
                lambda x: isinstance(x[1], Task),
                vars(module).items()
            )
            if not candidates:
                # Recurse downwards towards FS
                pass
            for name, task in candidates:
                collection.add_task(
                    name=name,
                    task=task,
                    aliases=task.aliases,
                    default=task.is_default
                )
            return collection
        except ImportError, e:
            # TODO: Handle ImportErrors that aren't "<name does not exist>"
            # I.e. if there is some inner ImportError or similar raising from
            # the attempt to import 'name' module.
            raise CollectionNotFound(name=name, root=self.root, error=e)

    def load_collection(self, name=None):
        """
        Load collection named ``name``.

        If not given, looks for a ``"tasks"`` collection by default.
        """
        if name is None:
            # TODO: make this configurable
            name = 'tasks'
        c = Collection()
        # add root to system path
        sys.path = self.update_path(sys.path)
        # add task candidates to collection
        collection = self.add_to_collection(name, c)
        return collection
