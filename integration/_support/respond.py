"""
Basic program that will exit nonzero when it's not correctly 'replied' to.
"""

import sys


if raw_input("What's the password?") != "Rosebud":
    sys.exit(1)
