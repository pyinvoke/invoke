"""
Program that just does busywork, yields stdout/stderr and ignores stdin.

Useful for measuring CPU usage of the code interfacing with it without
expecting the test environment to have much of anything.

Accepts a single argv argument, which is the number of cycles to run.
"""

import sys
import time


num_cycles = int(sys.argv[1])

for i in range(num_cycles):
    out = "[{}] This is my stdout, there are many like it, but...\n".format(i)
    print(out, file=sys.stdout, flush=True)
    err = "[{}] To err is human, to stderr is superhuman\n".format(i)
    print(out, file=sys.stderr, flush=True)
    time.sleep(0.1)
