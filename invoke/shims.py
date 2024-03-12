import shlex
import sys
from typing import List


if sys.version_info >= (3, 8):

    def shlex_join(split_command: List) -> str:
        """Convert command from list to str."""
        return shlex.join(split_command)

else:

    def shlex_join(split_command: List) -> str:
        """Convert command from list to str."""
        return shlex.quote(" ".join(split_command))[1:-1]
