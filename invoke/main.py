"""
Invoke's own 'binary' entrypoint.

Dogfoods the `program` module.
"""

from ._version import __version__
from .program import Program


program = Program(name="Invoke", binary='inv[oke]', version=__version__)
