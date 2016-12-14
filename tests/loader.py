import imp
import os
import sys

from spec import Spec, eq_, raises

from invoke.loader import Loader, FilesystemLoader as FSLoader
from invoke.collection import Collection
from invoke.exceptions import CollectionNotFound

from _util import support


class _BasicLoader(Loader):
    """
    Tests top level Loader behavior with basic finder stub.

    Used when we want to make sure we're testing Loader.load and not e.g.
    FilesystemLoader's specific implementation.
    """
    def find(self, name):
        self.fd, self.path, self.desc = t = imp.find_module(name, [support])
        return t


class Loader_(Spec):
    def adds_module_parent_dir_to_sys_path(self):
        # Crummy doesn't-explode test.
        _BasicLoader().load('namespacing')

    def doesnt_dupliate_parent_dir_addition(self):
        _BasicLoader().load('namespacing')
        _BasicLoader().load('namespacing')
        # If the bug is present, this will be 2 at least (and often more, since
        # other tests will pollute it (!).
        eq_(sys.path.count(support), 1)

    def closes_opened_file_object(self):
        loader = _BasicLoader()
        loader.load('foo')
        assert loader.fd.closed

    def can_load_package(self):
        loader = _BasicLoader()
        # make sure it doesn't explode
        loader.load('package')


class FilesystemLoader_(Spec):
    def setup(self):
        self.l = FSLoader(start=support)

    def exposes_discovery_start_point(self):
        start = '/tmp/'
        eq_(FSLoader(start=start).start, start)

    def has_a_default_discovery_start_point(self):
        eq_(FSLoader().start, os.getcwd())

    def returns_collection_object_if_name_found(self):
        result = self.l.load('foo')
        eq_(type(result), Collection)

    @raises(CollectionNotFound)
    def raises_CollectionNotFound_if_not_found(self):
        self.l.load('nope')

    @raises(ImportError)
    def raises_ImportError_if_found_collection_cannot_be_imported(self):
        # Instead of masking with a CollectionNotFound
        self.l.load('oops')

    def searches_towards_root_of_filesystem(self):
        # Loaded while root is in same dir as .py
        directly = self.l.load('foo')
        # Loaded while root is multiple dirs deeper than the .py
        deep = os.path.join(support, 'ignoreme', 'ignoremetoo')
        indirectly = FSLoader(start=deep).load('foo')
        eq_(directly, indirectly)

    def defaults_to_tasks_collection(self):
        "defaults to 'tasks' collection"
        # There's a basic tasks.py in tests/_support
        result = self.l.load()
        eq_(type(result), Collection)
