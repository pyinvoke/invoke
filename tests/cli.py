from invoke.collection import Collection
from invoke.parser import Parser
from invoke.tasks import task


class CLIParsing:
    """
    High level parsing tests
    """

    def setup_method(self):
        @task(positional=[], iterable=["my_list"], incrementable=["verbose"])
        def my_task(
            c,
            mystring,
            s,
            boolean=False,
            b=False,
            v=False,
            long_name=False,
            true_bool=True,
            _leading_underscore=False,
            trailing_underscore_=False,
            my_list=None,
            verbose=0,
        ):
            pass

        @task(aliases=["my_task27"])
        def my_task2(c):
            pass

        @task(default=True)
        def my_task3(c, mystring):
            pass

        @task
        def my_task4(c, clean=False, browse=False):
            pass

        @task(aliases=["other"], default=True)
        def sub_task(c):
            pass

        @task
        def implicit_positionals(c, pos1, pos2, nonpos="default"):
            pass

        @task(positional=["pos1", "pos2"])
        def explicit_positionals(c, pos1=1, pos2=2, nonpos="default"):
            pass

        sub_coll = Collection("sub_coll", sub_task)
        self.c = Collection(
            my_task,
            my_task2,
            my_task3,
            my_task4,
            sub_coll,
            implicit_positionals,
            explicit_positionals,
        )

    def _parser(self):
        return Parser(self.c.to_contexts())

    def _parse(self, argstr):
        return self._parser().parse_argv(argstr.split())

    def _compare(self, invoke, flagname, value):
        invoke = "my-task " + invoke
        result = self._parse(invoke)
        assert result[0].args[flagname].value == value

    def _compare_names(self, given, real):
        assert self._parse(given)[0].name == real

    def underscored_flags_can_be_given_as_dashed(self):
        self._compare("--long-name", "long_name", True)

    def leading_underscores_are_ignored(self):
        self._compare("--leading-underscore", "_leading_underscore", True)

    def trailing_underscores_are_ignored(self):
        self._compare("--trailing-underscore", "trailing_underscore_", True)

    def inverse_boolean_flags(self):
        self._compare("--no-true-bool", "true_bool", False)

    def namespaced_task(self):
        self._compare_names("sub-coll.sub-task", "sub-coll.sub-task")

    def aliases(self):
        self._compare_names("my-task27", "my-task2")

    def subcollection_aliases(self):
        self._compare_names("sub-coll.other", "sub-coll.sub-task")

    def subcollection_default_tasks(self):
        self._compare_names("sub-coll", "sub-coll.sub-task")

    def boolean_args(self):
        "my-task --boolean"
        self._compare("--boolean", "boolean", True)

    def flag_then_space_then_value(self):
        "my-task --mystring foo"
        self._compare("--mystring foo", "mystring", "foo")

    def flag_then_equals_sign_then_value(self):
        "my-task --mystring=foo"
        self._compare("--mystring=foo", "mystring", "foo")

    def short_boolean_flag(self):
        "my-task -b"
        self._compare("-b", "b", True)

    def short_flag_then_space_then_value(self):
        "my-task -s value"
        self._compare("-s value", "s", "value")

    def short_flag_then_equals_sign_then_value(self):
        "my-task -s=value"
        self._compare("-s=value", "s", "value")

    def short_flag_with_adjacent_value(self):
        "my-task -svalue"
        r = self._parse("my-task -svalue")
        assert r[0].args.s.value == "value"

    def _flag_value_task(self, value):
        r = self._parse("my-task -s {} my-task2".format(value))
        assert len(r) == 2
        assert r[0].name == "my-task"
        assert r[0].args.s.value == value
        assert r[1].name == "my-task2"

    def flag_value_then_task(self):
        "my-task -s value my-task2"
        self._flag_value_task("value")

    def flag_value_same_as_task_name(self):
        "my-task -s my-task2 my-task2"
        self._flag_value_task("my-task2")

    def three_tasks_with_args(self):
        "my-task --boolean my-task3 --mystring foo my-task2"
        r = self._parse("my-task --boolean my-task3 --mystring foo my-task2")
        assert len(r) == 3
        assert [x.name for x in r] == ["my-task", "my-task3", "my-task2"]
        assert r[0].args.boolean.value
        assert r[1].args.mystring.value == "foo"

    def tasks_with_duplicately_named_kwargs(self):
        "my-task --mystring foo my-task3 --mystring bar"
        r = self._parse("my-task --mystring foo my-task3 --mystring bar")
        assert r[0].name == "my-task"
        assert r[0].args.mystring.value == "foo"
        assert r[1].name == "my-task3"
        assert r[1].args.mystring.value == "bar"

    def multiple_short_flags_adjacent(self):
        "my-task -bv (and inverse)"
        for args in ("-bv", "-vb"):
            r = self._parse("my-task {}".format(args))
            a = r[0].args
            assert a.b.value
            assert a.v.value

    def list_type_flag_can_be_given_N_times_building_a_list(self):
        "my-task --my-list foo --my-list bar"
        # Test both the singular and plural cases, just to be safe.
        self._compare("--my-list foo", "my-list", ["foo"])
        self._compare("--my-list foo --my-list bar", "my-list", ["foo", "bar"])

    def incrementable_type_flag_can_be_used_as_a_switch_or_counter(self):
        "my-task -v, -vv, -vvvvv etc, except with explicit --verbose"
        self._compare("", "verbose", 0)
        self._compare("--verbose", "verbose", 1)
        self._compare("--verbose --verbose --verbose", "verbose", 3)

    # TODO:
    # - implicit posargs:
    #   - not given: boom
    #   - given solo
    #   - given before a flag
    #   - given after a flag
    #   - given /as/ a flag instead
    #   - ambiguity with optional-value flags (should be another test that can
    #   be cloned/modified?)
    # - explicit posargs:
    #   - all of the above repeated...
    #   - explicitly-given-as-positional-but-is-kwarg-with-default:
    #       - should work if not given (supplies default)
    #       - work if given positionally
    #       - AND work if given as a flag
    #   - same as above, but with MORE THAN ONE posarg-as-kwarg in a row:
    #       - all given positionally: fine
    #       - all given as flags: fine
    #       - first posarg given positionally only: fine
    #       - the weird one: first posarg given as flag, second posarg given as
    #       positional - this should still work, right? the parser side of
    #       "what was I given positionally?" should just look at "what
    #       remaining task-level posargs remain after parsing all the flags?"
    #           - but also, how does this intersect with eg true-flags/bools?
    #   - implicit-and-not-listed-explicitly posargs, not given as
    #   explicit-flag format: boom
    #   - "  " but given as explicit-flag format: works ok

    def explicit_positionals_may_have_default_values(self):
        # TODO: reuse this as one of above cases when debugged lol
        # TODO: or rename the test I guess, it's confusing
        r = self._parse("explicit-positionals 7 8 --nonpos custom")
        assert r[0].args.pos1.value == 7
        assert r[0].args.pos2.value == 8
        assert r[0].args.nonpos.value == "custom"

    def explicit_positionals_with_defaults_may_not_mask_other_tasks(self):
        r = self._parse("explicit-positionals 7 sub-task")
        assert len(r) == 2  # two tasks!
        assert r[0].args.pos1.value == 7  # given on CLI positionally
        assert r[0].args.pos2.value == 2  # default kwarg value
        assert r[0].args.nonpos.value == "default"  # default kwarg value
        assert r[1].name == "sub-task"
