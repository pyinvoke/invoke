from contextlib import contextmanager
from resource import getrusage, RUSAGE_SELF
import sys
import time

from invoke.vendor.six import wraps

from pytest import skip


def current_cpu_usage():
    rusage = getrusage(RUSAGE_SELF)
    return rusage.ru_utime + rusage.ru_stime


@contextmanager
def assert_cpu_usage(lt, verbose=False):
    """
    Execute wrapped block, asserting CPU utilization was less than ``lt``%.

    :param float lt: CPU use percentage above which failure will occur.
    :param bool verbose: Whether to print out the calculated percentage.
    """
    start_usage = current_cpu_usage()
    start_time = time.time()
    yield
    end_usage = current_cpu_usage()
    end_time = time.time()

    usage_diff = end_usage - start_usage
    time_diff = end_time - start_time

    if time_diff == 0: # Apparently possible!
        time_diff = 0.000001

    percentage = (usage_diff / time_diff) * 100.0

    if verbose:
        print("Used {0:.2}% CPU over {1:.2}s".format(percentage, time_diff))

    assert percentage < lt


def only_utf8(f):
    """
    Decorator causing tests to skip if local shell pipes aren't UTF-8.
    """
    # TODO: use actual test selection labels or whatever nose has
    @wraps(f)
    def inner(*args, **kwargs):
        if getattr(sys.stdout, 'encoding', None) == 'UTF-8':
            return f(*args, **kwargs)
        # TODO: could remove this so they show green, but figure yellow is more
        # appropriate
        skip()
    return inner
