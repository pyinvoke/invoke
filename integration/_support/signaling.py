"""
Used to make assertions about signals received when called as a subprocess.

Omits use of Invoke helpers for cleaner testing (less nesting).
"""

import signal
import sys

from invoke.vendor import six


#
# Handlers & friends
#

def _timeout(signum, frame):
    raise Exception("Never received any signals!")

def _hr(signum):
    name = None
    for key, value in six.iteritems(signal.__dict__):
        if value == signum:
            name = key
            break
    return name or "signal {0}".format(signum)

def _fail(signum, frame):
    raise Exception("Received unexpected {0}".format(_hr(signum)))

def _succeed(signum, frame):
    # NOTE: had to end up using 'any output == problem' to communicate with
    # test runner, so that makes us a good Unix utility I guess - no news is
    # good news.
    pass


#
# Subroutines
#

def wait():
    # Set timeout handler
    signal.signal(signal.SIGALRM, _timeout)
    # NOTE: in most cases, 1s shoul be plenty of time, but if race conditions
    # appear, this is the first thing to try changing.
    # NOTE: may want to sleep longer than 1s in order to accomodate an
    # outer-layer sleep which is ensuring we actually get to this point (vs
    # signaling during interpreter setup or the top of expect())
    signal.alarm(2)
    # Wait for a sign~
    signal.pause()


def expect(name):
    """
    Expect to receive signal ``name`` and not any other signal.

    Will also set things up so a timeout is set, to avoid hanging forever.
    """
    # Set common handle-able signals to a handler which excepts, by default
    for suffix in "HUP INT QUIT PIPE TERM".split():
        signame = "SIG{0}".format(suffix)
        signum = getattr(signal, signame)
        signal.signal(signum, _fail)
    # Then override the handler for the signal we're expecting, to exit OK
    signal.signal(getattr(signal, name), _succeed)
    # Then wait for a signal (this will also override SIGALRM)
    wait()


if __name__ == "__main__":
    expect(sys.argv[1])
