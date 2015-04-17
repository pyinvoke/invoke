from spec import Spec


class Runner_(Spec):
    class run:
        def out_stream_defaults_to_sys_stdout(self):
            "out_stream defaults to sys.stdout"

        def err_stream_defaults_to_sys_stderr(self):
            "err_stream defaults to sys.stderr"

        def out_stream_can_be_overridden(self):
            "out_stream can be overridden"

        def err_stream_can_be_overridden(self):
            "err_stream can be overridden"
