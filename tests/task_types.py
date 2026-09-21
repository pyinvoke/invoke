from pathlib import Path

from mypy import api


class TaskReturnTypes:
    def returns_the_body_result_type(self):
        source = Path(__file__).parent / "_support" / "task_return_types.py"
        stdout, stderr, status = api.run(
            [
                "--follow-imports=silent",
                "--warn-unused-ignores",
                str(source),
            ]
        )
        assert status == 0, stdout + stderr
