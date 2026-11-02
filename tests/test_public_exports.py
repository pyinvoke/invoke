import invoke
import invoke.parser
import pytest

EXPECTED_INVOKE_EXPORTS = [
    "Collection",
    "Config",
    "Context",
    "MockContext",
    "Exit",
    "Failure",
    "Result",
    "Runner",
    "Local",
    "Executor",
    "Task",
    "Call",
    "task",
    "call",
    "CollectionNotFound",
    "Program",
    "Argument",
    "Parser",
    "ParserContext",
    "ParseResult",
    "pty_size",
    "Responder",
]

EXPECTED_PARSER_EXPORTS = [
    "Parser",
    "ParseResult",
    "ParserContext",
    "Context",
    "to_flag",
    "translate_underscores",
    "Argument",
]


def test_invoke_defines_explicit_export_list():
    all_ = getattr(invoke, "__all__", None)
    assert isinstance(all_, (list, tuple)), (
        "invoke must define __all__ listing its public re-exports "
        "so mypy --no-implicit-reexport accepts 'from invoke import task'; "
        "fix by defining __all__ in invoke/__init__.py"
    )


@pytest.mark.parametrize("name", EXPECTED_INVOKE_EXPORTS)
def test_invoke_export_list_includes_expected_name(name):
    all_ = getattr(invoke, "__all__", [])
    assert name in all_, (
        "invoke.__all__ is missing {!r}; add it to __all__ in "
        "invoke/__init__.py so it is an explicit re-export".format(name)
    )


def test_invoke_star_import_exposes_task_without_leaking_internals():
    namespace = {}
    exec("from invoke import *", namespace)
    assert "task" in namespace, (
        "'from invoke import *' must expose 'task'; "
        "fix by exporting 'task' via __all__ in invoke/__init__.py"
    )
    assert "metadata" not in namespace, (
        "'from invoke import *' leaked 'metadata'; "
        "fix by defining __all__ in invoke/__init__.py "
        "containing only the public API"
    )


def test_parser_defines_explicit_export_list():
    all_ = getattr(invoke.parser, "__all__", None)
    assert isinstance(all_, (list, tuple)), (
        "invoke.parser must define __all__ listing its public re-exports "
        "so mypy --no-implicit-reexport accepts its consumers; "
        "fix by defining __all__ in invoke/parser/__init__.py"
    )


@pytest.mark.parametrize("name", EXPECTED_PARSER_EXPORTS)
def test_parser_export_list_includes_expected_name(name):
    all_ = getattr(invoke.parser, "__all__", [])
    assert name in all_, (
        "invoke.parser.__all__ is missing {!r}; add it to __all__ in "
        "invoke/parser/__init__.py so it is an explicit re-export".format(
            name
        )
    )
