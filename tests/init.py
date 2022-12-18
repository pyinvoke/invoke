import re

import six

from unittest.mock import patch

import invoke
import invoke.collection
import invoke.exceptions
import invoke.tasks
import invoke.program


class Init:
    "__init__"

    def dunder_version_info(self):
        assert hasattr(invoke, "__version_info__")
        ver = invoke.__version_info__
        assert isinstance(ver, tuple)
        assert all(isinstance(x, int) for x in ver)

    def dunder_version(self):
        assert hasattr(invoke, "__version__")
        ver = invoke.__version__
        assert isinstance(ver, str)
        assert re.match(r"\d+\.\d+\.\d+", ver)

    def dunder_version_looks_generated_from_dunder_version_info(self):
        # Meh.
        ver_part = invoke.__version__.split(".")[0]
        ver_info_part = invoke.__version_info__[0]
        assert ver_part == str(ver_info_part)

    class exposes_bindings:
        def task_decorator(self):
            assert invoke.task is invoke.tasks.task

        def task_class(self):
            assert invoke.Task is invoke.tasks.Task

        def collection_class(self):
            assert invoke.Collection is invoke.collection.Collection

        def context_class(self):
            assert invoke.Context is invoke.context.Context

        def mock_context_class(self):
            assert invoke.MockContext is invoke.context.MockContext

        def config_class(self):
            assert invoke.Config is invoke.config.Config

        def pty_size_function(self):
            assert invoke.pty_size is invoke.terminals.pty_size

        def local_class(self):
            assert invoke.Local is invoke.runners.Local

        def runner_class(self):
            assert invoke.Runner is invoke.runners.Runner

        def promise_class(self):
            assert invoke.Promise is invoke.runners.Promise

        def failure_class(self):
            assert invoke.Failure is invoke.runners.Failure

        def exceptions(self):
            # Meh
            for obj in vars(invoke.exceptions).values():
                if isinstance(obj, type) and issubclass(obj, BaseException):
                    top_level = getattr(invoke, obj.__name__)
                    real = getattr(invoke.exceptions, obj.__name__)
                    assert top_level is real

        def runner_result(self):
            assert invoke.Result is invoke.runners.Result

        def watchers(self):
            assert invoke.StreamWatcher is invoke.watchers.StreamWatcher
            assert invoke.Responder is invoke.watchers.Responder
            assert invoke.FailingResponder is invoke.watchers.FailingResponder

        def program(self):
            assert invoke.Program is invoke.program.Program

        def filesystemloader(self):
            assert invoke.FilesystemLoader is invoke.loader.FilesystemLoader

        def argument(self):
            assert invoke.Argument is invoke.parser.Argument

        def parsercontext(self):
            assert invoke.ParserContext is invoke.parser.ParserContext

        def parser(self):
            assert invoke.Parser is invoke.parser.Parser

        def parseresult(self):
            assert invoke.ParseResult is invoke.parser.ParseResult

        def executor(self):
            assert invoke.Executor is invoke.executor.Executor

        def call(self):
            assert invoke.call is invoke.tasks.call

        def Call(self):
            # Starting to think we shouldn't bother with lowercase-c call...
            assert invoke.Call is invoke.tasks.Call

    class offers_singletons:
        @patch("invoke.Context")
        def run(self, Context):
            result = invoke.run("foo", bar="biz")
            ctx = Context.return_value
            ctx.run.assert_called_once_with("foo", bar="biz")
            assert result is ctx.run.return_value

        @patch("invoke.Context")
        def sudo(self, Context):
            result = invoke.sudo("foo", bar="biz")
            ctx = Context.return_value
            ctx.sudo.assert_called_once_with("foo", bar="biz")
            assert result is ctx.sudo.return_value
