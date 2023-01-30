<<<<<<< HEAD
__version_info__ = (2, 0, 0)
__version__ = ".".join(map(str, __version_info__))
=======
from importlib_metadata import version  # type: ignore

__version__ = version(__package__)
__version_info__ = tuple(map(int, __version__.split('.')))
>>>>>>> 2093cf98 (github editor)
