from spec import Spec, skip, eq_, raises

from invoke.collection import Collection
from invoke.tasks import task, Task


@task
def _mytask():
    print "woo!"


class Collection_(Spec):
    class init:
        "__init__"
        def can_accept_task_varargs(self):
            "can accept tasks as *args"
            @task
            def task1():
                pass
            @task
            def task2():
                pass
            c = Collection(task1, task2)
            assert 'task1' in c
            assert 'task2' in c

        def can_accept_collections_as_varargs_too(self):
            sub = Collection('sub')
            ns = Collection(sub)
            eq_(ns.collections['sub'], sub)

        def kwargs_act_as_name_args_for_given_objects(self):
            sub = Collection()
            @task
            def task1():
                pass
            ns = Collection(loltask=task1, notsub=sub)
            eq_(ns['loltask'], task1)
            eq_(ns.collections['notsub'], sub)

        def initial_string_arg_acts_as_name(self):
            sub = Collection('sub')
            ns = Collection(sub)
            eq_(ns.collections['sub'], sub)

        def initial_string_arg_meshes_with_varargs_and_kwargs(self):
            # Collection('myname', atask, acollection, othertask=taskobj, ...)
            @task
            def task1():
                pass
            @task
            def task2():
                pass
            sub = Collection('sub')
            ns = Collection('root', task1, sub, sometask=task2)
            for x, y in (
                (ns.name, 'root'),
                (ns['task1'], task1),
                (ns.collections['sub'], sub),
                (ns['sometask'], task2),
            ):
                eq_(x, y)

    class from_module:
        def _load(self, name):
            sys.path.insert(0, '_support')
            mod = __import__(name)
            sys.path.pop(0)
            return mod

        def adds_tasks(self):
            c = Collection.from_module(self._load('integration'))
            assert 'print_foo' in c

        def adds_collections(self):
            skip()

        def skips_non_root_collections(self):
            # Aka ones not named 'namespace' or 'ns'
            skip()

    class add_task:
        def setup(self):
            self.c = Collection()

        def associates_given_callable_with_given_name(self):
            self.c.add_task(_mytask, 'foo')
            eq_(self.c['foo'], _mytask)

        def uses_function_name_as_implicit_name(self):
            self.c.add_task(_mytask)
            assert '_mytask' in self.c

        @raises(ValueError)
        def raises_ValueError_if_no_name_and_non_function(self):
            # Can't use a lambda here as they are technically real functions.
            class Callable(object):
                def __call__(self):
                    pass
            self.c.add_task(Task(Callable()))

        def allows_specifying_aliases(self):
            self.c.add_task(_mytask, 'foo', aliases=('bar',))
            eq_(self.c['bar'], _mytask)

        def allows_specifying_multiple_aliases(self):
            self.c.add_task(_mytask, 'foo', aliases=('bar', 'biz'))
            eq_(self.c['bar'], _mytask)
            eq_(self.c['biz'], _mytask)

        def allows_flagging_as_default(self):
            self.c.add_task(_mytask, 'foo', default=True)
            eq_(self.c[''], _mytask)

        @raises(ValueError)
        def raises_ValueError_on_multiple_defaults(self):
            self.c.add_task(_mytask, 'foo', default=True)
            self.c.add_task(_mytask, 'bar', default=True)

    class add_collection:
        def adds_collection_as_subcollection_of_self(self):
            skip()

        def can_take_module_objects(self):
            skip()

        @raises(ValueError)
        def raises_ValueError_if_collection_without_name(self):
            # Aka non-root collections must either have an explicit name given
            # via kwarg, have a name attribute set, or be a module with
            # __name__ defined.
            root = Collection()
            sub = Collection()
            root.add_collection(sub)

    class getitem:
        "__getitem__"
        def setup(self):
            self.c = Collection()

        def finds_own_tasks_by_name(self):
            # TODO: duplicates an add_task test above, fix?
            self.c.add_task(_mytask, 'foo')
            eq_(self.c['foo'], _mytask)

        def finds_subcollection_tasks_by_dotted_name(self):
            sub = Collection('sub')
            sub.add_task(_mytask)
            self.c.add_collection(sub)
            eq_(self.c['sub._mytask'], _mytask)

        def honors_aliases_in_own_tasks(self):
            self.c.add_task(_mytask, 'foo', aliases=('bar',))
            eq_(self.c['bar'], _mytask)

        def honors_subcollection_task_aliases(self):
            skip()

        def honors_own_default_task_with_no_args(self):
            self.c.add_task(_mytask, 'foo', default=True)
            eq_(self.c[''], _mytask)

        def honors_subcollection_default_tasks_on_subcollection_name(self):
            skip()

        def is_aliased_to_dunder_getitem(self):
            self.c.add_task(_mytask, 'foo')
            eq_(self.c['foo'], _mytask)

        def honors_own_default_task_getitem(self):
            self.c.add_task(_mytask, 'foo', default=True)
            eq_(self.c[''], _mytask)

        @raises(ValueError)
        def raises_ValueError_for_no_name_and_no_default(self):
            self.c['']

    class to_contexts:
        def setup(self):
            @task
            def mytask(text, boolean=False, number=5):
                print text
            @task
            def mytask2():
                pass
            self.c = Collection(mytask, mytask2)
            self.contexts = self.c.to_contexts()
            self.context = self.contexts[1]

        def returns_iterable_of_Contexts_corresponding_to_tasks(self):
            eq_(self.context.name, 'mytask')
            eq_(len(self.contexts), 2)

        def allows_flaglike_access_via_flags(self):
            assert '--text' in self.context.flags

        def positional_arglist_preserves_order_given(self):
            @task(positional=('second', 'first'))
            def mytask(first, second, third):
                pass
            c = Collection()
            c.add_task(mytask)
            ctx = c.to_contexts()[0]
            eq_(ctx.positional_args, [ctx.args['second'], ctx.args['first']])
