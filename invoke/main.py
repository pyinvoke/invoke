"""
Invoke's own 'binary' entrypoint.

Dogfoods the `program` module.
"""

from .program import Program


program = Program(
    # Reflect that we're installed as both 'inv' and 'invoke' in help output
    binary='inv[oke]',
)
