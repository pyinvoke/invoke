from spec import eq_, Spec

from invoke.collection import Collection
from invoke.parser import Parser
from invoke.tasks import task


class CLIParsing(Spec):
    """
    High level parsing tests
    """
    def setup(self):
        @task(positional=[])
        def my_task(ctx, mystring, s, boolean=False, b=False, v=False,
            long_name=False, true_bool=True, _leading_underscore=False,
            trailing_underscore_=False):
            pass
        @task(aliases=['my_task27'])
        def my_task2(ctx):
            pass
        @task(default=True)
        def my_task3(ctx, mystring):
            pass
        @task
        def my_task4(ctx, clean=False, browse=False):
            pass
        @task(aliases=['other'], default=True)
        def sub_task(ctx):
            pass
        sub_coll = Collection('sub_coll', sub_task)
        self.c = Collection(my_task, my_task2, my_task3, my_task4, sub_coll)

    def _parser(self):
        return Parser(self.c.to_contexts())

    def _parse(self, argstr):
        return self._parser().parse_argv(argstr.split())

    def _compare(self, invoke, flagname, value):
        invoke = "my_task " + invoke
        result = self._parse(invoke)
        eq_(result[0].args[flagname].value, value)

    def _compare_names(self, given, real):
        eq_(self._parse(given)[0].name, real)

    def underscored_flags_can_be_given_as_dashed(self):
        self._compare('--long-name', 'long_name', True)

    def leading_underscores_are_ignored(self):
        self._compare('--leading-underscore', '_leading_underscore', True)

    def trailing_underscores_are_ignored(self):
        self._compare('--trailing-underscore', 'trailing_underscore_', True)

    def inverse_boolean_flags(self):
        self._compare('--no-true-bool', 'true_bool', False)

    def namespaced_task(self):
        self._compare_names("sub_coll.sub_task", "sub_coll.sub_task")

    def aliases(self):
        self._compare_names("my-task27", "my-task2")

    def subcollection_aliases(self):
        self._compare_names("sub_coll.other", "sub_coll.sub_task")

    def subcollection_default_tasks(self):
        self._compare_names("sub_coll", "sub.sub_task")

    def boolean_args(self):
        "my_task --boolean"
        self._compare("--boolean", 'boolean', True)

    def flag_then_space_then_value(self):
        "my_task --mystring foo"
        self._compare("--mystring foo", 'mystring', 'foo')

    def flag_then_equals_sign_then_value(self):
        "my_task --mystring=foo"
        self._compare("--mystring=foo", 'mystring', 'foo')

    def short_boolean_flag(self):
        "my_task -b"
        self._compare("-b", 'b', True)

    def short_flag_then_space_then_value(self):
        "my_task -s value"
        self._compare("-s value", 's', 'value')

    def short_flag_then_equals_sign_then_value(self):
        "my_task -s=value"
        self._compare("-s=value", 's', 'value')

    def short_flag_with_adjacent_value(self):
        "my_task -svalue"
        r = self._parse("my_task -svalue")
        eq_(r[0].args.s.value, 'value')

    def _flag_value_task(self, value):
        r = self._parse("my_task -s {0} my_task2".format(value))
        eq_(len(r), 2)
        eq_(r[0].name, 'my_task')
        eq_(r[0].args.s.value, value)
        eq_(r[1].name, 'my_task2')

    def flag_value_then_task(self):
        "my_task -s value my_task2"
        self._flag_value_task('value')

    def flag_value_same_as_task_name(self):
        "my_task -s my_task2 my_task2"
        self._flag_value_task('my_task2')

    def three_tasks_with_args(self):
        "my_task --boolean my_task3 --mystring foo my_task2"
        r = self._parse("my_task --boolean my_task3 --mystring foo my_task2")
        eq_(len(r), 3)
        eq_([x.name for x in r], ['my_task', 'my_task3', 'my_task2'])
        eq_(r[0].args.boolean.value, True)
        eq_(r[1].args.mystring.value, 'foo')

    def tasks_with_duplicately_named_kwargs(self):
        "my_task --mystring foo my_task3 --mystring bar"
        r = self._parse("my_task --mystring foo my_task3 --mystring bar")
        eq_(r[0].name, 'my_task')
        eq_(r[0].args.mystring.value, 'foo')
        eq_(r[1].name, 'my_task3')
        eq_(r[1].args.mystring.value, 'bar')

    def multiple_short_flags_adjacent(self):
        "my_task -bv (and inverse)"
        for args in ('-bv', '-vb'):
            r = self._parse("my_task {0}".format(args))
            a = r[0].args
            eq_(a.b.value, True)
            eq_(a.v.value, True)
