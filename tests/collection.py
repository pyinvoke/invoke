from spec import Spec, skip, eq_, raises

from invoke.collection import Collection


def _mytask():
    print "woo!"


class Collection_(Spec):
    class add_task:
        def associates_given_callable_with_given_name(self):
            c = Collection()
            c.add_task('foo', _mytask)
            eq_(c.get('foo'), _mytask)

        def allows_specifying_aliases(self):
            c = Collection()
            c.add_task('foo', _mytask, aliases=('bar',))
            eq_(c.get('bar'), _mytask)

        def allows_specifying_multiple_aliases(self):
            c = Collection()
            c.add_task('foo', _mytask, aliases=('bar', 'biz'))
            eq_(c.get('bar'), _mytask)
            eq_(c.get('biz'), _mytask)

        def allows_flagging_as_default(self):
            c = Collection()
            c.add_task('foo', _mytask, default=True)
            eq_(c.get(), _mytask)

        @raises(ValueError)
        def raises_ValueError_on_multiple_defaults(self):
            c = Collection()
            c.add_task('foo', _mytask, default=True)
            c.add_task('bar', _mytask, default=True)

    class add_collection:
        def adds_collection_as_subcollection_of_self(self):
            skip()

    class get:
        def finds_own_tasks_by_name(self):
            # TODO: duplicates an add_task test above, fix?
            c = Collection()
            c.add_task('foo', _mytask)
            eq_(c.get('foo'), _mytask)

        def finds_subcollection_tasks_by_dotted_name(self):
            skip()

        def honors_aliases_in_own_tasks(self):
            c = Collection()
            c.add_task('foo', _mytask, aliases=('bar',))
            eq_(c.get('bar'), _mytask)

        def honors_subcollection_aliases(self):
            skip()

        def honors_own_default_task_with_no_args(self):
            c = Collection()
            c.add_task('foo', _mytask, default=True)
            eq_(c.get(), _mytask)

        def honors_subcollection_default_tasks_on_subcollection_name(self):
            skip()

        def is_aliased_to_dunder_getitem(self):
            "is aliased to __getitem__"
            skip()
