from spec import Spec, skip, eq_, raises

from invoke.collection import Collection
from invoke.task import task


@task
def _mytask():
    print "woo!"


class Collection_(Spec):
    class add_task:
        def setup(self):
            self.c = Collection()

        def associates_given_callable_with_given_name(self):
            self.c.add_task('foo', _mytask)
            eq_(self.c.get('foo'), _mytask)

        def allows_specifying_aliases(self):
            self.c.add_task('foo', _mytask, aliases=('bar',))
            eq_(self.c.get('bar'), _mytask)

        def allows_specifying_multiple_aliases(self):
            self.c.add_task('foo', _mytask, aliases=('bar', 'biz'))
            eq_(self.c.get('bar'), _mytask)
            eq_(self.c.get('biz'), _mytask)

        def allows_flagging_as_default(self):
            self.c.add_task('foo', _mytask, default=True)
            eq_(self.c.get(), _mytask)

        @raises(ValueError)
        def raises_ValueError_on_multiple_defaults(self):
            self.c.add_task('foo', _mytask, default=True)
            self.c.add_task('bar', _mytask, default=True)

    class add_collection:
        def adds_collection_as_subcollection_of_self(self):
            skip()

    class get:
        def setup(self):
            self.c = Collection()

        def finds_own_tasks_by_name(self):
            # TODO: duplicates an add_task test above, fix?
            self.c.add_task('foo', _mytask)
            eq_(self.c.get('foo'), _mytask)

        def finds_subcollection_tasks_by_dotted_name(self):
            skip()

        def honors_aliases_in_own_tasks(self):
            self.c.add_task('foo', _mytask, aliases=('bar',))
            eq_(self.c.get('bar'), _mytask)

        def honors_subcollection_aliases(self):
            skip()

        def honors_own_default_task_with_no_args(self):
            self.c.add_task('foo', _mytask, default=True)
            eq_(self.c.get(), _mytask)

        def honors_subcollection_default_tasks_on_subcollection_name(self):
            skip()

        def is_aliased_to_dunder_getitem(self):
            "is aliased to __getitem__"
            skip()

        @raises(ValueError)
        def raises_ValueError_for_no_name_and_no_default(self):
            self.c.get()

    class to_contexts:
        def setup(self):
            @task
            def mytask(text, boolean=False, number=5):
                print text
            @task
            def mytask2():
                pass
            self.c = Collection()
            self.c.add_task('mytask', mytask)
            self.c.add_task('mytask2', mytask2)
            self.contexts = self.c.to_contexts()
            self.context = self.contexts[1]

        def returns_iterable_of_Contexts_corresponding_to_tasks(self):
            eq_(self.context.name, 'mytask')
            eq_(len(self.contexts), 2)

        def turns_function_signature_into_Arguments(self):
            eq_(len(self.context.args), 3)
            assert 'text' in self.context.args

        def boolean_default_arg_values_inform_Argument_kind_kwarg(self):
            a = self.context.args
            eq_(a.boolean.kind, bool)
            eq_(a.number.kind, int)

        def allows_flaglike_access_via_flags(self):
            assert '--text' in self.context.flags

        def autocreates_short_flags(self):
            a = self.context.args
            assert 't' in a
            assert a['t'] is a['text']

        def autocreated_short_flags_can_be_disabled(self):
            @task(auto_shortflags=False)
            def mytask(arg):
                pass
            col = Collection()
            col.add_task('mytask', mytask)
            args = col.to_contexts()[0].args
            assert 'a' not in args
            assert 'arg' in args

        def autocreated_short_flags_dont_clash_with_existing_flags(self):
            @task
            def mytask(arg1, arg2, barg):
                pass
            col = Collection()
            col.add_task('mytask', mytask)
            args = col.to_contexts()[0].args
            assert 'a' in args
            assert args['a'] is args['arg1']
            assert 'r' in args
            assert args['r'] is args['arg2']
            assert 'b' in args
            assert args['b'] is args['barg']
