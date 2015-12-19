from contextlib import contextmanager
from resource import getrusage, RUSAGE_SELF
import time


def current_cpu_usage():
    rusage = getrusage(RUSAGE_SELF)
    return rusage.ru_utime + rusage.ru_stime


@contextmanager
def assert_cpu_usage(lt):
    """
    Execute wrapped block, asserting CPU utilization was less than ``lt``%.
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

    assert percentage < lt
