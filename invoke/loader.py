import os
import sys
import imp

from .collection import Collection
from .exceptions import CollectionNotFound
from .tasks import Task
from .util import debug


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

        In addition to importing the named module, it will add the module's
        parent directory to the front of `sys.path` to provide normal Python
        import behavior (i.e. so the loaded module may load local-to-it modules
        or packages.)
        """
        # Find the named tasks module, depending on implementation.
        # Will raise an exception if not found.
        fd, path, desc = self.find(name)
        try:
            # Ensure containing directory is on sys.path in case the module
            # being imported is trying to load local-to-it names.
            sys.path.insert(0, os.path.dirname(path))
            # Actual import
            module = imp.load_module(name, fd, path, desc)
            # Make a collection from it, and done
            return Collection.from_module(module)
        finally:
            # Ensure we clean up the opened file object returned by find(), if
            # there was one (eg found packages, vs modules, don't open any
            # file.)
            if fd:
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
        debug("FilesystemLoader find starting at {0!r}".format(start))
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
            tup = imp.find_module(name, parents)
            debug("Found module: {0!r}".format(tup[1]))
            return tup
        except ImportError:
            raise CollectionNotFound(name=name, start=start)
