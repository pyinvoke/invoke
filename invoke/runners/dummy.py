from . import Runner


class Dummy(Runner):
    """
    Lazy/no-op runner designed for testing purposes.
    """
    # TODO: how to make it easier to actually use for tests? move some common
    # subroutines from test modules in here?
    # TODO: at minimum, document the techniques used in those subroutines (or
    # what I want/need to use for invocations testing) in here or in a
    # specific conceptual doc.
    # Neuter the input loop sleep, so tests aren't slow (at the expense of CPU,
    # which isn't a problem for testing).
    input_sleep = 0

    def start(self, command, shell, env):
        pass

    def read_proc_stdout(self, num_bytes):
        return ""

    def read_proc_stderr(self, num_bytes):
        return ""

    def _write_proc_stdin(self, data):
        pass

    @property
    def process_is_finished(self):
        return True

    def returncode(self):
        return 0

    def send_interrupt(self, exception):
        pass

    def stop(self):
        pass
