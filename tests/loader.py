import os
import sys

from spec import Spec, skip, eq_, raises

from invoke.loader import FilesystemLoader as Loader # TODO: expand
from invoke.collection import Collection
from invoke.exceptions import CollectionNotFound

from _utils import support


class Loader_(Spec):
    def exposes_discovery_start_point(self):
        start = '/tmp/'
        eq_(Loader(start=start).start, start)

    def has_a_default_discovery_start_point(self):
        eq_(Loader().start, os.getcwd())

    class load_collection:
        def setup(self):
            self.l = Loader(start=support)

        def returns_collection_object_if_name_found(self):
            result = self.l.load_collection('foo')
            eq_(type(result), Collection)

        @raises(CollectionNotFound)
        def raises_CollectionNotFound_if_not_found(self):
            self.l.load_collection('nope')

        @raises(ImportError)
        def raises_ImportError_if_found_collection_cannot_be_imported(self):
            # Instead of masking with a CollectionNotFound
            self.l.load_collection('oops')

        def searches_towards_root_of_filesystem(self):
            # Loaded while root is in same dir as .py
            directly = self.l.load_collection('foo')
            # Loaded while root is multiple dirs deeper than the .py
            deep = os.path.join(support, 'ignoreme', 'ignoremetoo')
            indirectly = Loader(start=deep).load_collection('foo')
            eq_(directly, indirectly)

        def defaults_to_tasks_collection(self):
            "defaults to 'tasks' collection"
            result = Loader(start=support + '/implicit/').load_collection()
            eq_(type(result), Collection)

    class find_collection:
        @raises(CollectionNotFound)
        def raises_CollectionNotFound_for_missing_collections(self):
            result = Loader(start=support).find_collection('nope')

    class update_path:
        def setup(self):
            self.l = Loader(start=support)

        def does_not_modify_argument(self):
            path = []
            new_path = self.l.update_path(path)
            eq_(path, [])
            assert len(new_path) > 0

        def inserts_self_start_parent_at_front_of_path(self):
            "Inserts self.start at front of path"
            eq_(self.l.update_path([])[0], self.l.start)

        def adds_to_front_if_exists(self):
            "Inserts self.start at front of path even if it's already elsewhere"
            new_path = self.l.update_path([self.l.start])
            eq_(len(new_path), 2) # lol ?
            eq_(new_path[0], self.l.start)
