import sys

if raw_input("standard out") != "with it":
    sys.exit(1)

# Since raw_input(text) defaults to stdout...
sys.stderr.write("standard error")
sys.stderr.flush()
if raw_input() != "between chair and keyboard":
    sys.exit(1)
