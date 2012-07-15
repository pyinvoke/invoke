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

        def adds_parent_to_path(self):
            loader = Loader(root=support)
            loader.add_parent_to_path()
            eq_(sys.path[0], os.path.abspath(support))

        def gets_collection_object_if_name_found(self):
            c = Collection()
            loader = Loader(root=support)
            loader.add_parent_to_path()
            result = loader.get_collections('foo', c)
            eq_(type(result), Collection)

        @raises(CollectionNotFound)
        def get_collection_raises_CollectioNotFound(self):
            c = Collection()
            result = Loader(root=support).get_collections('nope', c)

        @raises(CollectionNotFound)
        def raises_CollectionNotFound_if_not_found(self):
            Loader(root=support).load_collection('nope')

        def raises_InvalidCollection_if_invalid(self):
            skip()

        def honors_discovery_root_option(self):
            skip()

        def searches_towards_root_of_filesystem(self):
            skip()

        def only_adds_valid_task_objects(self):
            skip()

        def adds_actual_tasks_not_just_task_bodies(self):
            skip()

        def adds_valid_subcollection_objects(self):
            skip()

        def defaults_to_tasks_collection(self):
            "defaults to 'tasks' collection"
            result = Loader(root=support + '/implicit/').load_collection()
            eq_(type(result), Collection)

    class load:
        def returns_nested_collection_from_all_given_names(self):
            skip()

        def uses_first_collection_as_root_namespace(self):
            skip()

        def raises_CollectionNotFound_if_any_names_not_found(self):
            skip()

        def raises_InvalidCollection_if_any_found_modules_invalid(self):
            skip()
