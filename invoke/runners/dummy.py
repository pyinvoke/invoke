from . import Runner


class Dummy(Runner):
    """
    Dummy runner subclass that does minimum work required to execute run().

    It also serves as a convenient basic API checker; failure to update it to
    match the current Runner API will cause TypeErrors, NotImplementedErrors,
    and similar.
    """
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
