from pathlib import Path
import subprocess
import sys

from pytest import importorskip


def dependency_annotations_accept_tasks_and_calls():
    importorskip("mypy")
    fixture = Path(__file__).parent / "_support" / "task_dependency_types.py"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict-equality",
            "--follow-imports=silent",
            "--warn-unused-ignores",
            str(fixture),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
