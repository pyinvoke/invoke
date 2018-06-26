import imp
import os
import sys
import types

from pytest import raises

from invoke import Config
from invoke.loader import Loader, FilesystemLoader as FSLoader
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


class Loader_:
    def exhibits_default_config_object(self):
        loader = _BasicLoader()
        assert isinstance(loader.config, Config)
        assert loader.config.tasks.collection_name == "tasks"

    def returns_module_and_location(self):
        mod, path = _BasicLoader().load("namespacing")
        assert isinstance(mod, types.ModuleType)
        assert path == support

    def may_configure_config_via_constructor(self):
        config = Config({"tasks": {"collection_name": "mytasks"}})
        loader = _BasicLoader(config=config)
        assert loader.config.tasks.collection_name == "mytasks"

    def adds_module_parent_dir_to_sys_path(self):
        # Crummy doesn't-explode test.
        _BasicLoader().load("namespacing")

    def doesnt_dupliate_parent_dir_addition(self):
        _BasicLoader().load("namespacing")
        _BasicLoader().load("namespacing")
        # If the bug is present, this will be 2 at least (and often more, since
        # other tests will pollute it (!).
        assert sys.path.count(support) == 1

    def closes_opened_file_object(self):
        loader = _BasicLoader()
        loader.load("foo")
        assert loader.fd.closed

    def can_load_package(self):
        loader = _BasicLoader()
        # make sure it doesn't explode
        loader.load("package")

    def load_name_defaults_to_config_tasks_collection_name(self):
        "load() name defaults to config.tasks.collection_name"

        class MockLoader(_BasicLoader):
            def find(self, name):
                # Sanity
                assert name == "simple_ns_list"
                return super(MockLoader, self).find(name)

        config = Config({"tasks": {"collection_name": "simple_ns_list"}})
        loader = MockLoader(config=config)
        # More sanity: expect simple_ns_list.py (not tasks.py)
        mod, path = loader.load()
        assert mod.__file__ == os.path.join(support, "simple_ns_list.py")


class FilesystemLoader_:
    def setup(self):
        self.l = FSLoader(start=support)

    def discovery_start_point_defaults_to_cwd(self):
        assert FSLoader().start == os.getcwd()

    def exposes_start_point_as_attribute(self):
        assert FSLoader().start == os.getcwd()

    def start_point_is_configurable_via_kwarg(self):
        start = "/tmp/"
        assert FSLoader(start=start).start == start

    def start_point_is_configurable_via_config(self):
        config = Config({"tasks": {"search_root": "nowhere"}})
        assert FSLoader(config=config).start == "nowhere"

    def raises_CollectionNotFound_if_not_found(self):
        with raises(CollectionNotFound):
            self.l.load("nope")

    def raises_ImportError_if_found_collection_cannot_be_imported(self):
        # Instead of masking with a CollectionNotFound
        with raises(ImportError):
            self.l.load("oops")

    def searches_towards_root_of_filesystem(self):
        # Loaded while root is in same dir as .py
        directly = self.l.load("foo")
        # Loaded while root is multiple dirs deeper than the .py
        deep = os.path.join(support, "ignoreme", "ignoremetoo")
        indirectly = FSLoader(start=deep).load("foo")
        assert directly == indirectly
