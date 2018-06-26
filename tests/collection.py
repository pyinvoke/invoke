from __future__ import print_function

import operator

from invoke.util import reduce

from pytest import raises

from invoke.collection import Collection
from invoke.tasks import task, Task

from _util import load, support_path


@task
def _mytask(c):
    print("woo!")


def _func(c):
    pass


class Collection_:
    class init:
        "__init__"

        def can_accept_task_varargs(self):
            "can accept tasks as *args"

            @task
            def task1(c):
                pass

            @task
            def task2(c):
                pass

            c = Collection(task1, task2)
            assert "task1" in c
            assert "task2" in c

        def can_accept_collections_as_varargs_too(self):
            sub = Collection("sub")
            ns = Collection(sub)
            assert ns.collections["sub"] == sub

        def kwargs_act_as_name_args_for_given_objects(self):
            sub = Collection()

            @task
            def task1(c):
                pass

            ns = Collection(loltask=task1, notsub=sub)
            assert ns["loltask"] == task1
            assert ns.collections["notsub"] == sub

        def initial_string_arg_acts_as_name(self):
            sub = Collection("sub")
            ns = Collection(sub)
            assert ns.collections["sub"] == sub

        def initial_string_arg_meshes_with_varargs_and_kwargs(self):
            @task
            def task1(c):
                pass

            @task
            def task2(c):
                pass

            sub = Collection("sub")
            ns = Collection("root", task1, sub, sometask=task2)
            for x, y in (
                (ns.name, "root"),
                (ns["task1"], task1),
                (ns.collections["sub"], sub),
                (ns["sometask"], task2),
            ):
                assert x == y

        def accepts_load_path_kwarg(self):
            assert Collection().loaded_from is None
            assert Collection(loaded_from="a/path").loaded_from == "a/path"

        def accepts_auto_dash_names_kwarg(self):
            assert Collection().auto_dash_names is True
            assert Collection(auto_dash_names=False).auto_dash_names is False

    class useful_special_methods:
        def _meh(self):
            @task
            def task1(c):
                pass

            @task
            def task2(c):
                pass

            @task
            def task3(c):
                pass

            submeh = Collection("submeh", task3)
            return Collection("meh", task1, task2, submeh)

        def setup(self):
            self.c = self._meh()

        def repr_(self):
            "__repr__"
            expected = "<Collection 'meh': task1, task2, submeh...>"
            assert expected == repr(self.c)

        def equality_consists_of_name_tasks_and_collections(self):
            # Truly equal
            assert self.c == self._meh()
            # Same contents, different name == not equal
            diffname = self._meh()
            diffname.name = "notmeh"
            assert diffname != self.c
            # And a sanity check that we didn't forget __ne__...cuz that
            # definitely happened at one point
            assert not diffname == self.c
            # Same name, same tasks, different collections == not equal
            diffcols = self._meh()
            del diffcols.collections["submeh"]
            assert diffcols != self.c
            # Same name, different tasks, same collections == not equal
            difftasks = self._meh()
            del difftasks.tasks["task1"]
            assert difftasks != self.c

        def boolean_is_equivalent_to_tasks_and_or_collections(self):
            # No tasks or colls? Empty/false
            assert not Collection()
            # Tasks but no colls? True
            @task
            def foo(c):
                pass

            assert Collection(foo)
            # Colls but no tasks: True
            assert Collection(foo=Collection(foo))
            # TODO: whether a tree that is not "empty" but has nothing BUT
            # other empty collections in it, should be true or false, is kinda
            # questionable - but since it would result in no usable task names,
            # let's say it's False. (Plus this lets us just use .task_names as
            # the shorthand impl...)
            assert not Collection(foo=Collection())

    class from_module:
        def setup(self):
            self.c = Collection.from_module(load("integration"))

        class parameters:
            def setup(self):
                self.mod = load("integration")
                self.from_module = Collection.from_module

            def name_override(self):
                assert self.from_module(self.mod).name == "integration"
                override = self.from_module(self.mod, name="not-integration")
                assert override.name == "not-integration"

            def inline_configuration(self):
                # No configuration given, none gotten
                assert self.from_module(self.mod).configuration() == {}
                # Config kwarg given is reflected when config obtained
                coll = self.from_module(self.mod, config={"foo": "bar"})
                assert coll.configuration() == {"foo": "bar"}

            def name_and_config_simultaneously(self):
                # Test w/ posargs to enforce ordering, just for safety.
                c = self.from_module(self.mod, "the name", {"the": "config"})
                assert c.name == "the name"
                assert c.configuration() == {"the": "config"}

            def auto_dash_names_passed_to_constructor(self):
                # Sanity
                assert self.from_module(self.mod).auto_dash_names is True
                # Test
                coll = self.from_module(self.mod, auto_dash_names=False)
                assert coll.auto_dash_names is False

        def adds_tasks(self):
            assert "print-foo" in self.c

        def derives_collection_name_from_module_name(self):
            assert self.c.name == "integration"

        def copies_docstring_from_module(self):
            expected = "A semi-integration-test style fixture spanning multiple feature examples."  # noqa
            # Checking the first line is sufficient.
            assert self.c.__doc__.strip().split("\n")[0] == expected

        def works_great_with_subclassing(self):
            class MyCollection(Collection):
                pass

            c = MyCollection.from_module(load("integration"))
            assert isinstance(c, MyCollection)

        def submodule_names_are_stripped_to_last_chunk(self):
            with support_path():
                from package import module
            c = Collection.from_module(module)
            assert module.__name__ == "package.module"
            assert c.name == "module"
            assert "mytask" in c  # Sanity

        def honors_explicit_collections(self):
            coll = Collection.from_module(load("explicit_root"))
            assert "top-level" in coll.tasks
            assert "sub-level" in coll.collections
            # The real key test
            assert "sub-task" not in coll.tasks

        def allows_tasks_with_explicit_names_to_override_bound_name(self):
            coll = Collection.from_module(load("subcollection_task_name"))
            assert "explicit-name" in coll.tasks  # not 'implicit_name'

        def returns_unique_Collection_objects_for_same_input_module(self):
            # Ignoring self.c for now, just in case it changes later.
            # First, a module with no root NS
            mod = load("integration")
            c1 = Collection.from_module(mod)
            c2 = Collection.from_module(mod)
            assert c1 is not c2
            # Now one *with* a root NS (which was previously buggy)
            mod2 = load("explicit_root")
            c3 = Collection.from_module(mod2)
            c4 = Collection.from_module(mod2)
            assert c3 is not c4

        class explicit_root_ns:
            def setup(self):
                mod = load("explicit_root")
                mod.ns.configure(
                    {
                        "key": "builtin",
                        "otherkey": "yup",
                        "subconfig": {"mykey": "myvalue"},
                    }
                )
                mod.ns.name = "builtin_name"
                self.unchanged = Collection.from_module(mod)
                self.changed = Collection.from_module(
                    mod,
                    name="override_name",
                    config={
                        "key": "override",
                        "subconfig": {"myotherkey": "myothervalue"},
                    },
                )

            def inline_config_with_root_namespaces_overrides_builtin(self):
                assert self.unchanged.configuration()["key"] == "builtin"
                assert self.changed.configuration()["key"] == "override"

            def inline_config_overrides_via_merge_not_replacement(self):
                assert "otherkey" in self.changed.configuration()

            def config_override_merges_recursively(self):
                subconfig = self.changed.configuration()["subconfig"]
                assert subconfig["mykey"] == "myvalue"

            def inline_name_overrides_root_namespace_object_name(self):
                assert self.unchanged.name == "builtin-name"
                assert self.changed.name == "override-name"

            def root_namespace_object_name_overrides_module_name(self):
                # Duplicates part of previous test for explicitness' sake.
                # I.e. proves that the name doesn't end up 'explicit_root'.
                assert self.unchanged.name == "builtin-name"

            def docstring_still_copied_from_module(self):
                expected = "EXPLICIT LYRICS"
                assert self.unchanged.__doc__.strip() == expected
                assert self.changed.__doc__.strip() == expected

    class add_task:
        def setup(self):
            self.c = Collection()

        def associates_given_callable_with_given_name(self):
            self.c.add_task(_mytask, "foo")
            assert self.c["foo"] == _mytask

        def uses_function_name_as_implicit_name(self):
            self.c.add_task(_mytask)
            assert "_mytask" in self.c

        def prefers_name_kwarg_over_task_name_attr(self):
            self.c.add_task(Task(_func, name="notfunc"), name="yesfunc")
            assert "yesfunc" in self.c
            assert "notfunc" not in self.c

        def prefers_task_name_attr_over_function_name(self):
            self.c.add_task(Task(_func, name="notfunc"))
            assert "notfunc" in self.c
            assert "_func" not in self.c

        def raises_ValueError_if_no_name_found(self):
            # Can't use a lambda here as they are technically real functions.
            class Callable(object):
                def __call__(self):
                    pass

            with raises(ValueError):
                self.c.add_task(Task(Callable()))

        def raises_ValueError_on_multiple_defaults(self):
            t1 = Task(_func, default=True)
            t2 = Task(_func, default=True)
            self.c.add_task(t1, "foo")
            with raises(ValueError):
                self.c.add_task(t2, "bar")

        def raises_ValueError_if_task_added_mirrors_subcollection_name(self):
            self.c.add_collection(Collection("sub"))
            with raises(ValueError):
                self.c.add_task(_mytask, "sub")

        def allows_specifying_task_defaultness(self):
            self.c.add_task(_mytask, default=True)
            assert self.c.default == "_mytask"

        def specifying_default_False_overrides_task_setting(self):
            @task(default=True)
            def its_me(c):
                pass

            self.c.add_task(its_me, default=False)
            assert self.c.default is None

        def allows_specifying_aliases(self):
            self.c.add_task(_mytask, aliases=("task1", "task2"))
            assert self.c["_mytask"] is self.c["task1"] is self.c["task2"]

        def aliases_are_merged(self):
            @task(aliases=("foo", "bar"))
            def biz(c):
                pass

            # NOTE: using tuple above and list below to ensure no type problems
            self.c.add_task(biz, aliases=["baz", "boz"])
            for x in ("foo", "bar", "biz", "baz", "boz"):
                assert self.c[x] is self.c["biz"]

    class add_collection:
        def setup(self):
            self.c = Collection()

        def adds_collection_as_subcollection_of_self(self):
            c2 = Collection("foo")
            self.c.add_collection(c2)
            assert "foo" in self.c.collections

        def can_take_module_objects(self):
            self.c.add_collection(load("integration"))
            assert "integration" in self.c.collections

        def raises_ValueError_if_collection_without_name(self):
            # Aka non-root collections must either have an explicit name given
            # via kwarg, have a name attribute set, or be a module with
            # __name__ defined.
            root = Collection()
            sub = Collection()
            with raises(ValueError):
                root.add_collection(sub)

        def raises_ValueError_if_collection_named_same_as_task(self):
            self.c.add_task(_mytask, "sub")
            with raises(ValueError):
                self.c.add_collection(Collection("sub"))

    class getitem:
        "__getitem__"

        def setup(self):
            self.c = Collection()

        def finds_own_tasks_by_name(self):
            # TODO: duplicates an add_task test above, fix?
            self.c.add_task(_mytask, "foo")
            assert self.c["foo"] == _mytask

        def finds_subcollection_tasks_by_dotted_name(self):
            sub = Collection("sub")
            sub.add_task(_mytask)
            self.c.add_collection(sub)
            assert self.c["sub._mytask"] == _mytask

        def honors_aliases_in_own_tasks(self):
            t = Task(_func, aliases=["bar"])
            self.c.add_task(t, "foo")
            assert self.c["bar"] == t

        def honors_subcollection_task_aliases(self):
            self.c.add_collection(load("decorators"))
            assert "decorators.bar" in self.c

        def honors_own_default_task_with_no_args(self):
            t = Task(_func, default=True)
            self.c.add_task(t)
            assert self.c[""] == t

        def honors_subcollection_default_tasks_on_subcollection_name(self):
            sub = Collection.from_module(load("decorators"))
            self.c.add_collection(sub)
            # Sanity
            assert self.c["decorators.biz"] is sub["biz"]
            # Real test
            assert self.c["decorators"] is self.c["decorators.biz"]

        def raises_ValueError_for_no_name_and_no_default(self):
            with raises(ValueError):
                self.c[""]

        def ValueError_for_empty_subcol_task_name_and_no_default(self):
            self.c.add_collection(Collection("whatever"))
            with raises(ValueError):
                self.c["whatever"]

    class to_contexts:
        def setup(self):
            @task
            def mytask(c, text, boolean=False, number=5):
                print(text)

            @task(aliases=["mytask27"])
            def mytask2(c):
                pass

            @task(aliases=["othertask"], default=True)
            def subtask(c):
                pass

            sub = Collection("sub", subtask)
            self.c = Collection(mytask, mytask2, sub)
            self.contexts = self.c.to_contexts()
            alias_tups = [list(x.aliases) for x in self.contexts]
            self.aliases = reduce(operator.add, alias_tups, [])
            # Focus on 'mytask' as it has the more interesting sig
            self.context = [x for x in self.contexts if x.name == "mytask"][0]

        def returns_iterable_of_Contexts_corresponding_to_tasks(self):
            assert self.context.name == "mytask"
            assert len(self.contexts) == 3

        class auto_dash_names:
            def context_names_automatically_become_dashed(self):
                @task
                def my_task(c):
                    pass

                contexts = Collection(my_task).to_contexts()
                assert contexts[0].name == "my-task"

            def percolates_to_subcollection_tasks(self):
                @task
                def outer_task(c):
                    pass

                @task
                def inner_task(c):
                    pass

                coll = Collection(outer_task, inner=Collection(inner_task))
                contexts = coll.to_contexts()
                expected = {"outer-task", "inner.inner-task"}
                assert {x.name for x in contexts} == expected

            def percolates_to_subcollection_names(self):
                @task
                def my_task(c):
                    pass

                coll = Collection(inner_coll=Collection(my_task))
                contexts = coll.to_contexts()
                assert contexts[0].name == "inner-coll.my-task"

            def aliases_are_dashed_too(self):
                @task(aliases=["hi_im_underscored"])
                def whatever(c):
                    pass

                contexts = Collection(whatever).to_contexts()
                assert "hi-im-underscored" in contexts[0].aliases

            def leading_and_trailing_underscores_are_not_affected(self):
                @task
                def _what_evers_(c):
                    pass

                @task
                def _inner_cooler_(c):
                    pass

                inner = Collection("inner", _inner_cooler_)
                contexts = Collection(_what_evers_, inner).to_contexts()
                expected = {"_what-evers_", "inner._inner-cooler_"}
                assert {x.name for x in contexts} == expected

            def _nested_underscores(self, auto_dash_names=None):
                @task(aliases=["other_name"])
                def my_task(c):
                    pass

                @task(aliases=["other_inner"])
                def inner_task(c):
                    pass

                # NOTE: explicitly not giving kwarg to subcollection; this
                # tests that the top-level namespace performs the inverse
                # transformation when necessary.
                sub = Collection("inner_coll", inner_task)
                return Collection(
                    my_task, sub, auto_dash_names=auto_dash_names
                )

            def honors_init_setting_on_topmost_namespace(self):
                coll = self._nested_underscores(auto_dash_names=False)
                contexts = coll.to_contexts()
                names = ["my_task", "inner_coll.inner_task"]
                aliases = [["other_name"], ["inner_coll.other_inner"]]
                assert sorted(x.name for x in contexts) == sorted(names)
                assert sorted(x.aliases for x in contexts) == sorted(aliases)

            def transforms_are_applied_to_explicit_module_namespaces(self):
                # Symptom when bug present: Collection.to_contexts() dies
                # because it iterates over .task_names (transformed) and then
                # tries to use results to access __getitem__ (no auto
                # transform...because in all other situations, task structure
                # keys are already transformed; but this wasn't the case for
                # from_module() with explicit 'ns' objects!)
                namespace = self._nested_underscores()

                class FakeModule(object):
                    __name__ = "my_module"
                    ns = namespace

                coll = Collection.from_module(
                    FakeModule(), auto_dash_names=False
                )
                # NOTE: underscores, not dashes
                expected = {"my_task", "inner_coll.inner_task"}
                assert {x.name for x in coll.to_contexts()} == expected

        def allows_flaglike_access_via_flags(self):
            assert "--text" in self.context.flags

        def positional_arglist_preserves_order_given(self):
            @task(positional=("second", "first"))
            def mytask(c, first, second, third):
                pass

            coll = Collection()
            coll.add_task(mytask)
            c = coll.to_contexts()[0]
            expected = [c.args["second"], c.args["first"]]
            assert c.positional_args == expected

        def exposes_namespaced_task_names(self):
            assert "sub.subtask" in [x.name for x in self.contexts]

        def exposes_namespaced_task_aliases(self):
            assert "sub.othertask" in self.aliases

        def exposes_subcollection_default_tasks(self):
            assert "sub" in self.aliases

        def exposes_aliases(self):
            assert "mytask27" in self.aliases

    class task_names:
        def setup(self):
            self.c = Collection.from_module(load("explicit_root"))

        def returns_all_task_names_including_subtasks(self):
            names = set(self.c.task_names.keys())
            assert names == {"top-level", "sub-level.sub-task"}

        def includes_aliases_and_defaults_as_values(self):
            names = self.c.task_names
            assert names["top-level"] == ["other-top"]
            subtask_names = names["sub-level.sub-task"]
            assert subtask_names == ["sub-level.other-sub", "sub-level"]

    class configuration:
        "Configuration methods"

        def setup(self):
            self.root = Collection()
            self.task = Task(_func, name="task")

        def basic_set_and_get(self):
            self.root.configure({"foo": "bar"})
            assert self.root.configuration() == {"foo": "bar"}

        def configure_performs_merging(self):
            self.root.configure({"foo": "bar"})
            assert self.root.configuration()["foo"] == "bar"
            self.root.configure({"biz": "baz"})
            assert set(self.root.configuration().keys()), {"foo" == "biz"}

        def configure_merging_is_recursive_for_nested_dicts(self):
            self.root.configure({"foo": "bar", "biz": {"baz": "boz"}})
            self.root.configure({"biz": {"otherbaz": "otherboz"}})
            c = self.root.configuration()
            assert c["biz"]["baz"] == "boz"
            assert c["biz"]["otherbaz"] == "otherboz"

        def configure_allows_overwriting(self):
            self.root.configure({"foo": "one"})
            assert self.root.configuration()["foo"] == "one"
            self.root.configure({"foo": "two"})
            assert self.root.configuration()["foo"] == "two"

        def call_returns_dict(self):
            assert self.root.configuration() == {}
            self.root.configure({"foo": "bar"})
            assert self.root.configuration() == {"foo": "bar"}

        def access_merges_from_subcollections(self):
            inner = Collection("inner", self.task)
            inner.configure({"foo": "bar"})
            self.root.configure({"biz": "baz"})
            # With no inner collection
            assert set(self.root.configuration().keys()) == {"biz"}
            # With inner collection
            self.root.add_collection(inner)
            keys = set(self.root.configuration("inner.task").keys())
            assert keys == {"foo", "biz"}

        def parents_overwrite_children_in_path(self):
            inner = Collection("inner", self.task)
            inner.configure({"foo": "inner"})
            self.root.add_collection(inner)
            # Before updating root collection's config, reflects inner
            assert self.root.configuration("inner.task")["foo"] == "inner"
            self.root.configure({"foo": "outer"})
            # After, reflects outer (since that now overrides)
            assert self.root.configuration("inner.task")["foo"] == "outer"

        def sibling_subcollections_ignored(self):
            inner = Collection("inner", self.task)
            inner.configure({"foo": "hi there"})
            inner2 = Collection("inner2", Task(_func, name="task2"))
            inner2.configure({"foo": "nope"})
            root = Collection(inner, inner2)
            assert root.configuration("inner.task")["foo"] == "hi there"
            assert root.configuration("inner2.task2")["foo"] == "nope"

        def subcollection_paths_may_be_dotted(self):
            leaf = Collection("leaf", self.task)
            leaf.configure({"key": "leaf-value"})
            middle = Collection("middle", leaf)
            root = Collection("root", middle)
            config = root.configuration("middle.leaf.task")
            assert config == {"key": "leaf-value"}

        def invalid_subcollection_paths_result_in_KeyError(self):
            # Straight up invalid
            with raises(KeyError):
                Collection("meh").configuration("nope.task")
            # Exists but wrong level (should be 'root.task', not just
            # 'task')
            inner = Collection("inner", self.task)
            with raises(KeyError):
                Collection("root", inner).configuration("task")

        def keys_dont_have_to_exist_in_full_path(self):
            # Kinda duplicates earlier stuff; meh
            # Key only stored on leaf
            leaf = Collection("leaf", self.task)
            leaf.configure({"key": "leaf-value"})
            middle = Collection("middle", leaf)
            root = Collection("root", middle)
            config = root.configuration("middle.leaf.task")
            assert config == {"key": "leaf-value"}
            # Key stored on mid + leaf but not root
            middle.configure({"key": "whoa"})
            assert root.configuration("middle.leaf.task") == {"key": "whoa"}

    class subcollection_from_path:
        def top_level_path(self):
            collection = Collection.from_module(load("tree"))
            build = collection.collections["build"]
            assert collection.subcollection_from_path("build") is build

        def nested_path(self):
            collection = Collection.from_module(load("tree"))
            docs = collection.collections["build"].collections["docs"]
            assert collection.subcollection_from_path("build.docs") is docs

        def invalid_path(self):
            # This is really just testing Lexicon/dict behavior but w/e, good
            # to be explicit, esp if we ever want this to become Exit or
            # another custom exception. (For now most/all callers manually
            # catch KeyError and raise Exit just to keep most Exit use high up
            # in the stack...)
            with raises(KeyError):
                collection = Collection.from_module(load("tree"))
                collection.subcollection_from_path("lol.whatever.man")

    class serialized:
        def empty_collection(self):
            expected = dict(
                name=None, help=None, tasks=[], default=None, collections=[]
            )
            assert expected == Collection().serialized()

        def empty_named_collection(self):
            expected = dict(
                name="foo", help=None, tasks=[], default=None, collections=[]
            )
            assert expected == Collection("foo").serialized()

        def empty_named_docstringed_collection(self):
            expected = dict(
                name="foo",
                help="Hi doc",
                tasks=[],
                default=None,
                collections=[],
            )
            coll = Collection("foo")
            coll.__doc__ = "Hi doc"
            assert expected == coll.serialized()

        def name_docstring_default_and_tasks(self):
            expected = dict(
                name="deploy",
                help="How to deploy our code and configs.",
                tasks=[
                    dict(
                        name="db",
                        help="Deploy to our database servers.",
                        aliases=["db-servers"],
                    ),
                    dict(
                        name="everywhere",
                        help="Deploy to all targets.",
                        aliases=[],
                    ),
                    dict(
                        name="web",
                        help="Update and bounce the webservers.",
                        aliases=[],
                    ),
                ],
                default="everywhere",
                collections=[],
            )
            with support_path():
                from tree import deploy

                coll = Collection.from_module(deploy)
            assert expected == coll.serialized()

        def name_docstring_default_tasks_and_collections(self):
            docs = dict(
                name="docs",
                help="Tasks for managing Sphinx docs.",
                tasks=[
                    dict(
                        name="all", help="Build all doc formats.", aliases=[]
                    ),
                    dict(
                        name="html", help="Build HTML output only.", aliases=[]
                    ),
                    dict(
                        name="pdf", help="Build PDF output only.", aliases=[]
                    ),
                ],
                default="all",
                collections=[],
            )
            python = dict(
                name="python",
                help="PyPI/etc distribution artifacts.",
                tasks=[
                    dict(
                        name="all",
                        help="Build all Python packages.",
                        aliases=[],
                    ),
                    dict(
                        name="sdist",
                        help="Build classic style tar.gz.",
                        aliases=[],
                    ),
                    dict(name="wheel", help="Build a wheel.", aliases=[]),
                ],
                default="all",
                collections=[],
            )
            expected = dict(
                name="build",
                help="Tasks for compiling static code and assets.",
                tasks=[
                    dict(
                        name="all",
                        help="Build all necessary artifacts.",
                        aliases=["everything"],
                    ),
                    dict(
                        name="c-ext",
                        help="Build our internal C extension.",
                        aliases=["ext"],
                    ),
                    dict(name="zap", help="A silly way to clean.", aliases=[]),
                ],
                default="all",
                collections=[docs, python],
            )
            with support_path():
                from tree import build

                coll = Collection.from_module(build)
            assert expected == coll.serialized()

        def unnamed_subcollections(self):
            subcoll = Collection()
            named_subcoll = Collection("hello")
            # We're binding to name 'subcoll', but subcoll itself has no .name
            # attribute/value, which is what's being tested. When bug present,
            # that fact will cause serialized() to die on sorted() when
            # comparing to named_subcoll (which has a string name).
            root = Collection(named_subcoll, subcoll=subcoll)
            expected = dict(
                name=None,
                default=None,
                help=None,
                tasks=[],
                collections=[
                    # Expect anonymous first since we sort them as if their
                    # name was the empty string.
                    dict(
                        tasks=[],
                        collections=[],
                        name=None,
                        default=None,
                        help=None,
                    ),
                    dict(
                        tasks=[],
                        collections=[],
                        name="hello",
                        default=None,
                        help=None,
                    ),
                ],
            )
            assert expected == root.serialized()
