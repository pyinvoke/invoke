from spec import Spec, eq_, ok_

from invoke.util import sort_names

class util_(Spec):
    class sort_names_:
        "sort_names"

        def sorts_single_hierarchy_lexically(self):
            eq_(sort_names(["a", "c", "b"]), ["a", "b", "c"])

        def sorts_hierarchy_levels_lexically(self):
            eq_(sort_names(["a", "c.b", "c.a", "b"]), ["a", "b", "c.a", "c.b"])

        def group_hierachies_by_parent_then_depth_then_child(self):
            eq_(
                sort_names(["a.another.more", "a.first", "a.alpha", "b"]),
                ["b", "a.alpha", "a.first", "a.another.more"]
            )
