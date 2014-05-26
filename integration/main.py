import os

from spec import Spec, trap, eq_

from invoke import run


def _output_eq(cmd, expected):
    return eq_(run(cmd).stdout, expected)


class Main(Spec):
    def setup(self):
        # Enter integration/ so Invoke loads its local tasks.py
        os.chdir(os.path.dirname(__file__))

    @trap
    def basic_invocation(self):
        _output_eq("invoke print_foo", "foo\n")

    @trap
    def shorthand_binary_name(self):
        _output_eq("inv print_foo", "foo\n")

    @trap
    def explicit_task_module(self):
        _output_eq("invoke --collection _explicit foo", "Yup\n")

    @trap
    def invocation_with_args(self):
        _output_eq(
            "invoke print_name --name whatevs",
            "whatevs\n"
        )
