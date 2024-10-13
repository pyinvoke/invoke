import os
import sys
from importlib.metadata import entry_points
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple, Union

from .config import Config
from .exceptions import CollectionNotFound
from .util import debug


class Loader:
    """
    Abstract class defining how to find/import a session's base `.Collection`.

    .. versionadded:: 1.0
    """

    def __init__(
        self, config: Optional["Config"] = None, **kwargs: Any
    ) -> None:
        """
        Set up a new loader with some `.Config`.

        :param config:
            An explicit `.Config` to use; it is referenced for loading-related
            config options. Defaults to an anonymous ``Config()`` if none is
            given.
        """
        self.config = Config() if config is None else config

    def find(self, name: str) -> Optional[Union[Iterable[Any], Any]]:
        """
        Implementation-specific finder method seeking collection ``name``.

        Must return module valid for use by repsective ``load`` implementation,
        which is typically a name string followed by the contents of the
        3-tuple returned by `importlib.module_from_spec` (``name``, ``loader``,
        ``origin``.)

        For a sample implementation, see `.FilesystemLoader`.

        .. versionadded:: 1.0
        """
        raise NotImplementedError

    def load(self, name: Optional[str] = None) -> Tuple[Any, str]:
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
        raise NotImplementedError


class FilesystemLoader(Loader):
    """
    Loads Python files from the filesystem (e.g. ``tasks.py``).

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

    def find(self, name: str) -> Optional[Any]:
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

    def load(self, name: Optional[str] = None) -> Tuple[Any, str]:
        if name is None:
            name = self.config.tasks.collection_name
        spec = self.find(name)
        if spec and spec.loader and spec.origin:
            # Typically either tasks.py or tasks/__init__.py
            source_file = Path(spec.origin)
            # Will be 'the dir tasks.py is in', or 'tasks/', in both cases this
            # is what wants to be in sys.path for "from . import sibling"
            enclosing_dir = source_file.parent
            # Will be "the directory above the spot that 'import tasks' found",
            # namely the parent of "your task tree", i.e. "where project level
            # config files are looked for". So, same as enclosing_dir for
            # tasks.py, but one more level up for tasks/__init__.py...
            module_parent = enclosing_dir
            if spec.parent:  # it is a package, so we have to go up again
                module_parent = module_parent.parent
            # Get the enclosing dir on the path
            enclosing_str = str(enclosing_dir)
            if enclosing_str not in sys.path:
                sys.path.insert(0, enclosing_str)
            # Actual import
            module = module_from_spec(spec)
            sys.modules[spec.name] = module  # so 'from . import xxx' works
            spec.loader.exec_module(module)
            # Return the module and the folder it was found in
            return module, str(module_parent)
        msg = "ImportError loading {!r}, raising ImportError"
        debug(msg.format(name))
        raise ImportError


class EntryPointLoader(Loader):
    """Load collections from entry point."""

    def __init__(self, config: Optional[Config] = None, **kwargs: Any) -> None:
        """Initialize entry point plugins for invoke."""
        self.group = kwargs.pop('group', None)
        super().__init__(config, **kwargs)

    def find(
        self, name: Optional[str] = None
    ) -> Union[Iterable[Any], Any]:
        """Find entrypoints for invoke."""
        params = {}
        if name:
            params['name'] = name
        if self.group:
            params['group'] = self.group
        modules = entry_points(**params)
        if modules:
            return modules
        elif self.group:
            if name:
                raise CollectionNotFound(
                    name=name or 'entry_point', start=self.group
                )
            else:
                raise ModuleNotFoundError(
                    'no entry point matching group %r found',
                    self.group,
                )
        raise ModuleNotFoundError('no entry points found')

    def load(self, name: Optional[str] = None) -> Tuple[Any, str]:
        """Load entrypoints for invoke."""
        modules = self.find(name)
        for module in modules:
            return (module.load(), os.getcwd())
        raise ImportError
