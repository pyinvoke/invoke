from spec import Spec, skip, eq_, raises

from invoke.collection import Collection
from invoke.tasks import task


@task
def _mytask():
    print "woo!"


class Collection_(Spec):
    class add_task:
        def setup(self):
            self.c = Collection()

        def associates_given_callable_with_given_name(self):
            self.c.add_task('foo', _mytask)
            eq_(self.c['foo'], _mytask)

        def allows_specifying_aliases(self):
            self.c.add_task('foo', _mytask, aliases=('bar',))
            eq_(self.c['bar'], _mytask)

        def allows_specifying_multiple_aliases(self):
            self.c.add_task('foo', _mytask, aliases=('bar', 'biz'))
            eq_(self.c['bar'], _mytask)
            eq_(self.c['biz'], _mytask)

        def allows_flagging_as_default(self):
            self.c.add_task('foo', _mytask, default=True)
            eq_(self.c[''], _mytask)

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
            eq_(self.c['foo'], _mytask)

        def finds_subcollection_tasks_by_dotted_name(self):
            skip()

        def honors_aliases_in_own_tasks(self):
            self.c.add_task('foo', _mytask, aliases=('bar',))
            eq_(self.c['bar'], _mytask)

        def honors_subcollection_aliases(self):
            skip()

        def honors_own_default_task_with_no_args(self):
            self.c.add_task('foo', _mytask, default=True)
            eq_(self.c[''], _mytask)

        def honors_subcollection_default_tasks_on_subcollection_name(self):
            skip()

        def is_aliased_to_dunder_getitem(self):
            self.c.add_task('foo', _mytask)
            eq_(self.c['foo'], _mytask)

        def honors_own_default_task_getitem(self):
            self.c.add_task('foo', _mytask, default=True)
            eq_(self.c[''], _mytask)

        @raises(ValueError)
        def raises_ValueError_for_no_name_and_no_default(self):
            self.c['']

    class to_contexts:
        def setup(self):
            @task(positional=[])
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

        def allows_flaglike_access_via_flags(self):
            assert '--text' in self.context.flags

        def positional_arglist_preserves_order_given(self):
            @task(positional=('second', 'first'))
            def mytask(first, second, third):
                pass
            c = Collection()
            c.add_task('mytask', mytask)
            ctx = c.to_contexts()[0]
            eq_(ctx.positional_args, [ctx.args['second'], ctx.args['first']])
