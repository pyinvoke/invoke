import sys

try:
    from invoke.vendor.six.moves import input
except ImportError:
    from six.moves import input

if input("standard out") != "with it":
    sys.exit(1)

# Since raw_input(text) defaults to stdout...
sys.stderr.write("standard error")
sys.stderr.flush()
if input() != "between chair and keyboard":
    sys.exit(1)
