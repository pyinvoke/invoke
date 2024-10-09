import os

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


def use_eploader_directly():
    basedir = os.path.dirname(__file__)
    source_path = os.path.join(basedir, '_support', 'entry_point')
    os.chdir(source_path)
    loader = EntryPointLoader(group='invoke')
    collection = loader.load('test')[0]
    assert isinstance(collection, Collection)
    assert 'mytask' in collection.tasks.keys()
    assert collection.collections == {}


def use_eploader_from_collection():
    basedir = os.path.dirname(__file__)
    source_path = os.path.join(basedir, '_support', 'entry_point')
    os.chdir(source_path)
    collection = Collection.from_entry_point(group='invoke', name='test')
    assert isinstance(collection, Collection)
    assert collection.name == 'test'
    assert 'mytask' in collection.tasks.keys()
    assert collection.collections == {}


def raises_ImportError_if_eploader_cannot_import_module():
    basedir = os.path.dirname(__file__)
    source_path = os.path.join(basedir, '_support', 'entry_point')
    os.chdir(source_path)
    # Instead of masking with a CollectionNotFound
    with raises(ModuleNotFoundError):
        loader = EntryPointLoader(group='oops')
        loader.find()


def raises_CollectionNotFound_is_eploader_cannot_find_collection():
    basedir = os.path.dirname(__file__)
    source_path = os.path.join(basedir, '_support', 'entry_point')
    os.chdir(source_path)
    # Instead of masking with a CollectionNotFound
    with raises(CollectionNotFound):
        loader = EntryPointLoader(group='invoke')
        loader.find(name='nope')
