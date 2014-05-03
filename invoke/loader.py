import os
import sys
import imp

from .collection import Collection
from .exceptions import CollectionNotFound
from .tasks import Task


class Loader(object):
    """
    Abstract class defining how to load a session's base `.Collection`.
    """
    def find(self, name):
        """
        Implementation-specific finder method seeking collection ``name``.

        Must return a 4-tuple valid for use by `imp.load_module`, which is
        typically a name string followed by the contents of the 3-tuple
        returned by `imp.find_module` (``file``, ``pathname``,
        ``description``.)

        For a sample implementation, see `FilesystemLoader`.
        """
        raise NotImplementedError

    def load(self, name='tasks'):
        """
        Load and return collection identified by ``name``.

        This method requires a working implementation of `.find` in order to
        function.
        """
        # Import. Errors during import will raise normally. Close the file
        # object that was opened within self.find().
        fd, path, desc = self.find(name)
        try:
            module = imp.load_module(name, fd, path, desc)
            return Collection.from_module(module)
        finally:
            fd.close()


class FilesystemLoader(Loader):
    """
    Loads Python files from the filesystem (e.g. ``tasks.py``.)

    Searches recursively towards filesystem root from a given start point.
    """
    def __init__(self, start=None):
        self._start = start

    @property
    def start(self):
        # Lazily determine default CWD
        return self._start or os.getcwd()

    def find(self, name):
        # Accumulate all parent directories
        start = self.start
        parents = [os.path.abspath(start)]
        parents.append(os.path.dirname(parents[-1]))
        while parents[-1] != parents[-2]:
            parents.append(os.path.dirname(parents[-1]))
        # Make sure we haven't got duplicates on the end
        if parents[-1] == parents[-2]:
            parents = parents[:-1]
        # Use find_module with our list of parents. ImportError from
        # find_module means "couldn't find" not "found and couldn't import" so
        # we turn it into a more obvious exception class.
        try:
            return imp.find_module(name, parents)
        except ImportError:
            raise CollectionNotFound(name=name, start=start)
