import os
import sys
from importlib.util import spec_from_file_location
from types import ModuleType
from pathlib import Path

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
        path = os.path.join(support, name)
        if os.path.exists(f"{path}.py"):
            path = f"{path}.py"
        elif os.path.exists(path):
            path = os.path.join(path, "__init__.py")
        spec = spec_from_file_location(name, path)
        return spec


class Loader_:
    def exhibits_default_config_object(self):
        loader = _BasicLoader()
        assert isinstance(loader.config, Config)
        assert loader.config.tasks.collection_name == "tasks"

    def returns_module_and_location(self):
        mod, path = _BasicLoader().load("namespacing")
        assert isinstance(mod, ModuleType)
        assert path == support

    def may_configure_config_via_constructor(self):
        config = Config({"tasks": {"collection_name": "mytasks"}})
        loader = _BasicLoader(config=config)
        assert loader.config.tasks.collection_name == "mytasks"

    def adds_module_parent_dir_to_sys_path(self):
        # Crummy doesn't-explode test.
        _BasicLoader().load("namespacing")

    def doesnt_duplicate_parent_dir_addition(self):
        _BasicLoader().load("namespacing")
        _BasicLoader().load("namespacing")
        # If the bug is present, this will be 2 at least (and often more, since
        # other tests will pollute it (!).
        assert sys.path.count(support) == 1

    def can_load_package(self):
        loader = _BasicLoader()
        # Load itself doesn't explode (tests 'from . import xxx' internally)
        mod, loc = loader.load("package")
        # Properties of returned values look as expected
        package = Path(support) / "package"
        assert loc == str(package)
        assert mod.__file__ == str(package / "__init__.py")

    def load_name_defaults_to_config_tasks_collection_name(self):
        "load() name defaults to config.tasks.collection_name"

        class MockLoader(_BasicLoader):
            def find(self, name):
                # Sanity
                assert name == "simple_ns_list"
                return super().find(name)

        config = Config({"tasks": {"collection_name": "simple_ns_list"}})
        loader = MockLoader(config=config)
        # More sanity: expect simple_ns_list.py (not tasks.py)
        mod, path = loader.load()
        assert mod.__file__ == os.path.join(support, "simple_ns_list.py")


class FilesystemLoader_:
    def setup_method(self):
        self.loader = FSLoader(start=support)

    def discovery_start_point_defaults_to_cwd(self):
        assert FSLoader().start == os.getcwd()

    def exposes_start_point_as_attribute(self):
        assert FSLoader().start == os.getcwd()

    def start_point_is_configurable_via_kwarg(self):
        start = "/tmp"
        assert FSLoader(start=start).start == start

    def start_point_is_configurable_via_config(self):
        config = Config({"tasks": {"search_root": "nowhere"}})
        assert FSLoader(config=config).start == "nowhere"

    def raises_CollectionNotFound_if_not_found(self):
        with raises(CollectionNotFound):
            self.loader.load("nope")

    def raises_ImportError_if_found_collection_cannot_be_imported(self):
        # Instead of masking with a CollectionNotFound
        with raises(ModuleNotFoundError):
            self.loader.load("oops")

    # TODO: Need CollectionImportError here

    def searches_towards_root_of_filesystem(self):
        # Loaded while root is in same dir as .py
        directly = self.loader.load("foo")
        # Loaded while root is multiple dirs deeper than the .py
        deep = os.path.join(support, "ignoreme", "ignoremetoo")
        indirectly = FSLoader(start=deep).load("foo")
        assert directly[0].__file__ == indirectly[0].__file__
        assert directly[0].__spec__ == indirectly[0].__spec__
        assert directly[1] == indirectly[1]
