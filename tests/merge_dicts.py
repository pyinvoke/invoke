from spec import Spec, eq_, raises, ok_
from invoke.config import merge_dicts, copy_dict, AmbiguousMergeError


class merge_dicts_(Spec):
    # NOTE: don't usually like doing true unit tests of low level plumbing -
    # prefer to infer it's all working by examining higher level behavior - but
    # sometimes it's necessary to more easily stamp out certain bugs.

    def merging_data_onto_empty_dict(self):
        d1 = {}
        d2 = {'foo': 'bar'}
        merge_dicts(d1, d2)
        eq_(d1, d2)

    def orthogonal_data_merges(self):
        d1 = {'foo': 'bar'}
        d2 = {'biz': 'baz'}
        merge_dicts(d1, d2)
        eq_(d1, {'foo': 'bar', 'biz': 'baz'})

    def updates_arg_values_win(self):
        d1 = {'foo': 'bar'}
        d2 = {'foo': 'notbar'}
        merge_dicts(d1, d2)
        eq_(d1, {'foo': 'notbar'})

    def non_dict_type_mismatch_overwrites_ok(self):
        d1 = {'foo': 'bar'}
        d2 = {'foo': [1, 2, 3]}
        merge_dicts(d1, d2)
        eq_(d1, {'foo': [1, 2, 3]})

    @raises(AmbiguousMergeError)
    def merging_dict_into_nondict_raises_error(self):
        # TODO: or...should it?! If a user really wants to take a pre-existing
        # config path and make it 'deeper' by overwriting e.g. a string with a
        # dict of strings (or whatever)...should they be allowed to?
        d1 = {'foo': 'bar'}
        d2 = {'foo': {'uh': 'oh'}}
        merge_dicts(d1, d2)

    @raises(AmbiguousMergeError)
    def merging_nondict_into_dict_raises_error(self):
        d1 = {'foo': {'uh': 'oh'}}
        d2 = {'foo': 'bar'}
        merge_dicts(d1, d2)

    def nested_leaf_values_merge_ok(self):
        d1 = {'foo': {'bar': {'biz': 'baz'}}}
        d2 = {'foo': {'bar': {'biz': 'notbaz'}}}
        merge_dicts(d1, d2)
        eq_(d1, {'foo': {'bar': {'biz': 'notbaz'}}})

    def mixed_branch_levels_merges_ok(self):
        d1 = {'foo': {'bar': {'biz': 'baz'}}, 'meh': 17, 'myown': 'ok'}
        d2 = {'foo': {'bar': {'biz': 'notbaz'}}, 'meh': 25}
        merge_dicts(d1, d2)
        eq_(d1, {'foo': {'bar': {'biz': 'notbaz'}}, 'meh': 25, 'myown': 'ok'})

    def dict_value_merges_are_not_references(self):
        core = {}
        coll = {'foo': {'bar': {'biz': 'coll value'}}}
        proj = {'foo': {'bar': {'biz': 'proj value'}}}
        # Initial merge - when bug present, this sets core['foo'] to the entire
        # 'foo' dict in 'proj' as a reference - meaning it 'links' back to the
        # 'proj' dict whenever other things are merged into it
        merge_dicts(core, proj)
        eq_(core, {'foo': {'bar': {'biz': 'proj value'}}})
        eq_(proj['foo']['bar']['biz'], 'proj value')
        # Identity tests can also prove the bug early
        ok_(core['foo'] is not proj['foo'], "Core foo is literally proj foo!")
        # Subsequent merge - just overwrites leaf values this time (thus no
        # real change, but this is what real config merge code does, so why
        # not)
        merge_dicts(core, proj)
        eq_(core, {'foo': {'bar': {'biz': 'proj value'}}})
        eq_(proj['foo']['bar']['biz'], 'proj value')
        # The problem merge - when bug present, core['foo'] references 'foo'
        # inside 'proj', so this ends up tweaking "core" but it actually
        # affects "proj" as well!
        merge_dicts(core, coll)
        # Expect that the core dict got the update from 'coll'...
        eq_(core, {'foo': {'bar': {'biz': 'coll value'}}})
        # BUT that 'proj' remains UNTOUCHED
        eq_(proj['foo']['bar']['biz'], 'proj value')


class copy_dict_(Spec):
    def returns_deep_copy_of_given_dict(self):
        # NOTE: not actual deepcopy...
        source = {'foo': {'bar': {'biz': 'baz'}}}
        copy = copy_dict(source)
        eq_(copy['foo']['bar'], source['foo']['bar'])
        ok_(copy['foo']['bar'] is not source['foo']['bar'])
        copy['foo']['bar']['biz'] = 'notbaz'
        eq_(source['foo']['bar']['biz'], 'baz')
