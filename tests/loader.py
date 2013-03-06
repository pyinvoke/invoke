import os
import sys

from spec import Spec, skip, eq_, raises

from invoke.loader import Loader
from invoke.collection import Collection
from invoke.exceptions import CollectionNotFound

from _utils import support


class Loader_(Spec):
    def exposes_discovery_root(self):
        root = '/tmp/'
        eq_(Loader(root=root).root, root)

    def has_a_default_discovery_root(self):
        eq_(Loader().root, os.getcwd())

    class load_collection:
        def returns_collection_object_if_name_found(self):
            result = Loader(root=support).load_collection('foo')
            eq_(type(result), Collection)

        @raises(CollectionNotFound)
        def raises_CollectionNotFound_if_not_found(self):
            Loader(root=support).load_collection('nope')

        @raises(ImportError)
        def raises_ImportError_if_found_collection_cannot_be_imported(self):
            # Instead of masking with a CollectionNotFound
            Loader(root=support).load_collection('oops')

        def honors_discovery_root_option(self):
            skip()

        def searches_towards_root_of_filesystem(self):
            skip()

        def defaults_to_tasks_collection(self):
            "defaults to 'tasks' collection"
            result = Loader(root=support + '/implicit/').load_collection()
            eq_(type(result), Collection)

        def honors_explicit_collections(self):
            result = Loader(root=support).load_collection('explicit_root')
            assert 'top_level' in result
            assert 'sub.sub_task' in result

    class find_collection:
        @raises(CollectionNotFound)
        def raises_CollectionNotFound_for_missing_collections(self):
            result = Loader(root=support).find_collection('nope')

    class update_path:
        def setup(self):
            self.l = Loader(root=support)

        def does_not_modify_argument(self):
            path = []
            new_path = self.l.update_path(path)
            eq_(path, [])
            assert len(new_path) > 0

        def inserts_self_root_parent_at_front_of_path(self):
            "Inserts self.root at front of path"
            eq_(self.l.update_path([])[0], self.l.root)

        def does_not_insert_if_exists(self):
            "Doesn't insert self.root if it's already in the path"
            new_path = self.l.update_path([self.l.root])
            eq_(len(new_path), 1) # not 2
