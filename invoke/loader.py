import os
import sys
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
from typing import Any, Optional, Tuple

from . import Config
from .exceptions import CollectionNotFound
from .util import debug


class Loader:
    """
    Abstract class defining how to find/import a session's base `.Collection`.

    .. versionadded:: 1.0
    """

    def __init__(self, config: Optional["Config"] = None) -> None:
        """
        Set up a new loader with some `.Config`.

        :param config:
            An explicit `.Config` to use; it is referenced for loading-related
            config options. Defaults to an anonymous ``Config()`` if none is
            given.
        """
        if config is None:
            config = Config()
        self.config = config

    def find(self, name: str) -> Optional[ModuleSpec]:
        """
        Implementation-specific finder method seeking collection ``name``.

        Must return a ModuleSpec valid for use by `importlib`, which is
        typically a name string followed by the contents of the 3-tuple
        returned by `importlib.module_from_spec` (``name``, ``loader``,
        ``origin``.)

        For a sample implementation, see `.FilesystemLoader`.

        .. versionadded:: 1.0
        """
        raise NotImplementedError

    def load(self, name: Optional[str] = None) -> Tuple[ModuleType, str]:
        """
        Load and return collection module identified by ``name``.

        This method requires a working implementation of `.find` in order to
        function.

        In addition to importing the named module, it will add the module's
        parent directory to the front of `sys.path` to provide normal Python
        import behavior (i.e. so the loaded module may load local-to-it modules
        or packages.)

        :returns:
            Two-tuple of ``(module, directory)`` where ``module`` is the
            collection-containing Python module object, and ``directory`` is
            the string path to the directory the module was found in.

        .. versionadded:: 1.0
        """
        if name is None:
            name = self.config.tasks.collection_name
        spec = self.find(name)
        if spec and spec.loader and spec.origin:
            path = spec.origin
            # Ensure containing directory is on sys.path in case the module
            # being imported is trying to load local-to-it names.
            if os.path.isfile(spec.origin):
                path = os.path.dirname(spec.origin)
            if path not in sys.path:
                sys.path.insert(0, path)
            # Actual import
            module = module_from_spec(spec)
            sys.modules[spec.name] = module  # so 'from . import xxx' works
            spec.loader.exec_module(module)
            return module, os.path.dirname(spec.origin)
        msg = "ImportError loading {!r}, raising ImportError"
        debug(msg.format(name))
        raise ImportError


class FilesystemLoader(Loader):
    """
    Loads Python files from the filesystem (e.g. ``tasks.py``.)

    Searches recursively towards filesystem root from a given start point.

    .. versionadded:: 1.0
    """

    # TODO: could introduce config obj here for transmission to Collection
    # TODO: otherwise Loader has to know about specific bits to transmit, such
    # as auto-dashes, and has to grow one of those for every bit Collection
    # ever needs to know
    def __init__(self, start: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if start is None:
            start = self.config.tasks.search_root
        self._start = start

    @property
    def start(self) -> str:
        # Lazily determine default CWD if configured value is falsey
        return self._start or os.getcwd()

    def find(self, name: str) -> Optional[ModuleSpec]:
        debug("FilesystemLoader find starting at {!r}".format(self.start))
        spec = None
        module = "{}.py".format(name)
        paths = self.start.split(os.sep)
        try:
            # walk the path upwards to check for dynamic import
            for x in reversed(range(len(paths) + 1)):
                path = os.sep.join(paths[0:x])
                if module in os.listdir(path):
                    spec = spec_from_file_location(
                        name, os.path.join(path, module)
                    )
                    break
                elif name in os.listdir(path) and os.path.exists(
                    os.path.join(path, name, "__init__.py")
                ):
                    basepath = os.path.join(path, name)
                    spec = spec_from_file_location(
                        name,
                        os.path.join(basepath, "__init__.py"),
                        submodule_search_locations=[basepath],
                    )
                    break
            if spec:
                debug("Found module: {!r}".format(spec))
                return spec
        except (FileNotFoundError, ModuleNotFoundError):
            msg = "ImportError loading {!r}, raising CollectionNotFound"
            debug(msg.format(name))
            raise CollectionNotFound(name=name, start=self.start)
        return None
