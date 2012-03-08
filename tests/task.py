from spec import Spec, skip, eq_

from invoke.task import task


class _Dummy(object):
    pass


class task_(Spec):
    "@task"

    def returns_original_object(self):
        dummy = _Dummy()
        eq_(task(dummy), dummy)

    def annotates_object_with_invoke_task_flag(self):
        dummy = _Dummy()
        assert hasattr(task(dummy), 'is_invoke_task')
        assert getattr(task(dummy), 'is_invoke_task') is True

    def allows_alias_specification(self):
        dummy = _Dummy()

    def has_aliases_argument(self):
        skip()
