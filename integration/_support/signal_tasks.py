from invoke import ctask


@ctask
def expect(c, subroutine, pty=True):
    """
    Call a subroutine within signaling.py, then sleep, waiting for a signal.

    Integration tests use this task to run a subroutine within signaling.py;
    those subroutines are the actual test bodies, which expect a given signal
    to be submitted to them and fail if they don't receive it within a timeout.

    This indirection is necessary in order to submit signals to a
    controlled-by-the-test-suite subprocess, without actually signaling the
    test runner itself.
    """
    c.run("python signaling.py {0}".format(subroutine), pty=pty)
