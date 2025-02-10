import os
import sys

import pytest
from pytest import raises

from invoke import Config, Collection
from invoke.loader import FilesystemLoader, EntryPointLoader
from invoke.exceptions import CollectionNotFound

from _util import support


class FSLoader:
    def setup_method(self):
        self.loader = FilesystemLoader(start=support)

    def discovery_start_point_defaults_to_cwd(self):
        assert FilesystemLoader().start == os.getcwd()

    def start_point_is_configurable_via_kwarg(self):
        start = "/tmp"
        assert FilesystemLoader(start=start).start == start

    def start_point_is_configurable_via_config(self):
        config = Config({"tasks": {"search_root": "nowhere"}})
        assert FilesystemLoader(config=config).start == "nowhere"

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
        indirectly = FilesystemLoader(start=deep).load("foo")
        assert directly[0].__file__ == indirectly[0].__file__
        assert directly[0].__spec__ == indirectly[0].__spec__
        assert directly[1] == indirectly[1]


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="requires python3.7 or higher",
)
def use_eploader_directly():
    loader = EntryPointLoader(group='invoke')
    collection = loader.load('test')[0]
    assert isinstance(collection, Collection)
    assert 'mytask' in collection.tasks.keys()
    assert collection.collections == {}


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="requires python3.7 or higher",
)
def use_eploader_from_collection():
    collection = Collection.from_entry_point(group='invoke', name='test')
    assert isinstance(collection, Collection)
    assert collection.name == 'test'
    assert 'mytask' in collection.tasks.keys()
    assert collection.collections == {}


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="requires python3.7 or higher",
)
def raises_ImportError_if_eploader_cannot_import_module():
    # Instead of masking with a CollectionNotFound
    with raises(ModuleNotFoundError):
        loader = EntryPointLoader(group='oops')
        loader.find()


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="requires python3.7 or higher",
)
def raises_CollectionNotFound_is_eploader_cannot_find_collection():
    with raises(CollectionNotFound):
        loader = EntryPointLoader(group='invoke')
        loader.find(name='nope')
