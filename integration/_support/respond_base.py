import sys

try:
    from invoke.vendor.six.moves import input
except ImportError:
    from six.moves import input

if input("What's the password?") != "Rosebud":
    sys.exit(1)
