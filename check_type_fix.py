"""
Standalone regression check for pyinvoke/invoke#1064.

DataProxy.__setitem__ (used by Config.__setitem__ via context.config[...] = ...)
was typed as accepting only `str` values, which caused mypy to flag valid,
commonly-used code like `context.config["some"] = True` as a type error
([assignment]) for downstream consumers of invoke.

This script writes a small standalone snippet reproducing the issue and runs
mypy against it *without* this repo's own pyproject.toml config in effect
(that config sets `disable_error_code = ["assignment"]`, which would mask the
very error class this bug is about). It exits non-zero if mypy reports an
[assignment] error, and exits 0 otherwise.

Run directly: `python check_type_fix.py`
"""
import subprocess
import sys
import tempfile
import os

SNIPPET = """
from invoke import Context

def use_config(context: Context) -> None:
    context.config["some"] = True
    context.config["other"] = 123
    context.config["mapping"] = {"a": 1}
"""


def main() -> None:
    repo_root = os.path.dirname(os.path.abspath(__file__))

    with tempfile.TemporaryDirectory() as tmpdir:
        snippet_path = os.path.join(tmpdir, "check_snippet.py")
        with open(snippet_path, "w") as f:
            f.write(SNIPPET)

        env = dict(os.environ)
        env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--ignore-missing-imports",
                snippet_path,
            ],
            # Run from the tmpdir (not repo_root) so mypy does NOT pick up
            # this repo's own pyproject.toml [tool.mypy] config, which sets
            # disable_error_code = ["assignment"] and would mask the bug.
            cwd=tmpdir,
            env=env,
            capture_output=True,
            text=True,
        )

    output = result.stdout + result.stderr
    print(output)

    if "[assignment]" in output:
        print(
            "FAIL: mypy reported an [assignment] error for assigning a "
            "non-str value to context.config[...]; DataProxy.__setitem__'s "
            "value annotation is too narrow."
        )
        sys.exit(1)

    print("PASS: mypy did not flag non-str assignment to context.config[...]")
    sys.exit(0)


if __name__ == "__main__":
    main()
