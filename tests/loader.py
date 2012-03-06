from spec import Spec, skip

from invoke.loader import Loader


class Loader_(Spec):
    def exposes_requested_collection_names(self):
        skip()

    def exposes_discovery_root(self):
        skip()

    def has_a_default_discovery_root(self):
        # cwd
        skip()

    def has_a_default_name_list(self):
        # 'tasks'
        skip()

    class load_collection:
        def returns_collection_object_if_name_found(self):
            skip()

        def raises_CollectionNotFound_if_not_found(self):
            skip()

        def raises_InvalidCollection_if_invalid(self):
            skip()

        def honors_discovery_root_option(self):
            skip()

    class load:
        def returns_nested_collection_from_all_given_names(self):
            skip()

        def uses_first_collection_as_root_namespace(self):
            skip()

        def raises_CollectionNotFound_if_any_names_not_found(self):
            skip()

        def raises_InvalidCollection_if_any_found_modules_invalid(self):
            skip()
