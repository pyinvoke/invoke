import pickle
import os
from os.path import join, expanduser

from spec import eq_, ok_, raises
from mock import patch, call

from invoke.runners import Local
from invoke.config import Config
from invoke.exceptions import (
    AmbiguousEnvVar, UncastableEnvVar, UnknownFileType
)
from invoke.vendor import six

from _util import IntegrationSpec, skip_if_windows


CONFIGS_PATH = 'configs'
TYPES = ('yaml', 'yml', 'json', 'python')

def _load(kwarg, type_):
    path = join(CONFIGS_PATH, type_ + "/")
    return Config(**{kwarg: path})

class Config_(IntegrationSpec):
    class class_attrs:
        # TODO: move all other non-data-bearing kwargs to this mode
        class prefix:
            def defaults_to_invoke(self):
                eq_(Config().prefix, 'invoke')

            @patch.object(Config, '_load_yaml')
            def informs_config_filenames(self, load_yaml):
                class MyConf(Config):
                    prefix = 'other'
                MyConf(system_prefix='dir/')
                load_yaml.assert_any_call('dir/other.yaml')

            def informs_env_var_prefix(self):
                os.environ['OTHER_FOO'] = 'bar'
                class MyConf(Config):
                    prefix = 'other'
                c = MyConf(defaults={'foo': 'notbar'})
                c.load_shell_env()
                eq_(c.foo, 'bar')

        class file_prefix:
            def defaults_to_None(self):
                eq_(Config().file_prefix, None)

            @patch.object(Config, '_load_yaml')
            def informs_config_filenames(self, load_yaml):
                class MyConf(Config):
                    file_prefix = 'other'
                MyConf(system_prefix='dir/')
                load_yaml.assert_any_call('dir/other.yaml')

        class env_prefix:
            def defaults_to_None(self):
                eq_(Config().env_prefix, None)

            def informs_env_vars_loaded(self):
                os.environ['OTHER_FOO'] = 'bar'
                class MyConf(Config):
                    env_prefix = 'other'
                c = MyConf(defaults={'foo': 'notbar'})
                c.load_shell_env()
                eq_(c.foo, 'bar')

    class global_defaults:
        def basic_settings(self):
            # Just a catchall for what the baseline config settings should
            # be...for some reason we're not actually capturing all of these
            # reliably (even if their defaults are often implied by the tests
            # which override them, e.g. runner tests around warn=True, etc).
            eq_(
                Config.global_defaults(), {
                    'run': {
                        'echo': False,
                        'echo_stdin': None,
                        'encoding': None,
                        'env': {},
                        'err_stream': None,
                        'fallback': True,
                        'hide': None,
                        'in_stream': None,
                        'out_stream': None,
                        'pty': False,
                        'replace_env': False,
                        'shell': '/bin/bash',
                        'warn': False,
                        'watchers': [],
                    },
                    'runners': {
                        'local': Local,
                    },
                    'sudo': {
                        'password': None,
                        'prompt': '[sudo] password: ',
                        'user': None,
                    },
                    'tasks': {
                        'dedupe': True,
                    },
                },
            )

    class init:
        "__init__"

        def can_be_empty(self):
            eq_(Config().__class__, Config) # derp

        @patch.object(Config, '_load_yaml')
        def configure_global_location_prefix(self, load_yaml):
            # This is a bit funky but more useful than just replicating the
            # same test farther down?
            Config(system_prefix='meh/')
            load_yaml.assert_any_call('meh/invoke.yaml')

        @skip_if_windows
        @patch.object(Config, '_load_yaml')
        def default_system_prefix_is_etc(self, load_yaml):
            # TODO: make this work on Windows somehow without being a total
            # tautology? heh.
            Config()
            load_yaml.assert_any_call('/etc/invoke.yaml')

        @patch.object(Config, '_load_yaml')
        def configure_user_location_prefix(self, load_yaml):
            Config(user_prefix='whatever/')
            load_yaml.assert_any_call('whatever/invoke.yaml')

        @patch.object(Config, '_load_yaml')
        def default_user_prefix_is_homedir_plus_dot(self, load_yaml):
            Config()
            load_yaml.assert_any_call(expanduser('~/.invoke.yaml'))

        @patch.object(Config, '_load_yaml')
        def configure_project_location(self, load_yaml):
            Config(project_home='someproject')
            load_yaml.assert_any_call(join('someproject', 'invoke.yaml'))

        @patch.object(Config, '_load_yaml')
        def configure_runtime_path(self, load_yaml):
            Config(runtime_path='some/path.yaml')
            load_yaml.assert_any_call('some/path.yaml')

        def accepts_defaults_dict_kwarg(self):
            c = Config(defaults={'super': 'low level'})
            eq_(c.super, 'low level')

        def overrides_dict_is_first_posarg(self):
            c = Config({'new': 'data', 'run': {'hide': True}})
            eq_(c.run.hide, True) # default is False
            eq_(c.run.warn, False) # in global defaults, untouched
            eq_(c.new, 'data') # data only present at overrides layer

        def overrides_dict_is_also_a_kwarg(self):
            c = Config(overrides={'run': {'hide': True}})
            eq_(c.run.hide, True)

        @patch.object(Config, 'post_init')
        def can_defer_post_init_step(self, post_init):
            Config()
            post_init.assert_called_once_with()
            post_init.reset_mock()
            Config(defer_post_init=True)
            ok_(not post_init.called)

    class basic_API:
        "Basic API components"

        def can_be_used_directly_after_init(self):
            # No load() here...
            c = Config({'lots of these': 'tests look similar'})
            eq_(c['lots of these'], 'tests look similar')

        def allows_dict_and_attr_access(self):
            # TODO: combine with tests for Context probably
            c = Config({'foo': 'bar'})
            eq_(c.foo, 'bar')
            eq_(c['foo'], 'bar')

        def nested_dict_values_also_allow_dual_access(self):
            # TODO: ditto
            c = Config({'foo': 'bar', 'biz': {'baz': 'boz'}})
            # Sanity check - nested doesn't somehow kill simple top level
            eq_(c.foo, 'bar')
            eq_(c['foo'], 'bar')
            # Actual check
            eq_(c.biz.baz, 'boz')
            eq_(c['biz']['baz'], 'boz')
            eq_(c.biz['baz'], 'boz')
            eq_(c['biz'].baz, 'boz')

        def attr_access_has_useful_error_msg(self):
            c = Config()
            try:
                c.nope
            except AttributeError as e:
                expected = """
No attribute or config key found for 'nope'

Valid keys: ['run', 'runners', 'sudo', 'tasks']

Valid real attributes: ['clear', 'clone', 'env_prefix', 'file_prefix', 'from_data', 'global_defaults', 'load_collection', 'load_files', 'load_shell_env', 'merge', 'paths', 'pop', 'popitem', 'post_init', 'prefix', 'setdefault', 'update']
""".strip() # noqa
                eq_(str(e), expected)
            else:
                assert False, "Didn't get an AttributeError on bad key!"

        def subkeys_get_merged_not_overwritten(self):
            # Ensures nested keys merge deeply instead of shallowly.
            defaults = {'foo': {'bar': 'baz'}}
            overrides = {'foo': {'notbar': 'notbaz'}}
            c = Config(defaults=defaults, overrides=overrides)
            eq_(c.foo.notbar, 'notbaz')
            eq_(c.foo.bar, 'baz')

        def is_iterable_like_dict(self):
            c = Config(defaults={'a': 1, 'b': 2})
            eq_(set(c.keys()), set(['a', 'b']))
            eq_(set(list(c)), set(['a', 'b']))

        def supports_readonly_dict_protocols(self):
            # Use single-keypair dict to avoid sorting problems in tests.
            c = Config(defaults={'foo': 'bar'})
            c2 = Config(defaults={'foo': 'bar'})
            ok_('foo' in c)
            ok_('foo' in c2) # mostly just to trigger loading :x
            eq_(c, c2)
            eq_(len(c), 1)
            eq_(c.get('foo'), 'bar')
            if six.PY2:
                eq_(c.has_key('foo'), True)  # noqa
                eq_(list(c.iterkeys()), ['foo'])
                eq_(list(c.itervalues()), ['bar'])
            eq_(list(c.items()), [('foo', 'bar')])
            eq_(list(six.iteritems(c)), [('foo', 'bar')])
            eq_(list(c.keys()), ['foo'])
            eq_(list(c.values()), ['bar'])

        class deletion_methods:
            def pop(self):
                # Root
                c = Config(defaults={'foo': 'bar'})
                eq_(c.pop('foo'), 'bar')
                eq_(c, {})
                # With the default arg
                eq_(c.pop('wut', 'fine then'), 'fine then')
                # Leaf (different key to avoid AmbiguousMergeError)
                c.nested = {'leafkey': 'leafval'}
                eq_(c.nested.pop('leafkey'), 'leafval')
                eq_(c, {'nested': {}})

            def delitem(self):
                "__delitem__"
                c = Config(defaults={'foo': 'bar'})
                del c['foo']
                eq_(c, {})
                c.nested = {'leafkey': 'leafval'}
                del c.nested['leafkey']
                eq_(c, {'nested': {}})

            def delattr(self):
                "__delattr__"
                c = Config(defaults={'foo': 'bar'})
                del c.foo
                eq_(c, {})
                c.nested = {'leafkey': 'leafval'}
                del c.nested.leafkey
                eq_(c, {'nested': {}})

            def clear(self):
                c = Config(defaults={'foo': 'bar'})
                c.clear()
                eq_(c, {})
                c.nested = {'leafkey': 'leafval'}
                c.nested.clear()
                eq_(c, {'nested': {}})

            def popitem(self):
                c = Config(defaults={'foo': 'bar'})
                eq_(c.popitem(), ('foo', 'bar'))
                eq_(c, {})
                c.nested = {'leafkey': 'leafval'}
                eq_(c.nested.popitem(), ('leafkey', 'leafval'))
                eq_(c, {'nested': {}})

        class modification_methods:
            def setitem(self):
                c = Config(defaults={'foo': 'bar'})
                c['foo'] = 'notbar'
                eq_(c.foo, 'notbar')
                del c['foo']
                c['nested'] = {'leafkey': 'leafval'}
                eq_(c, {'nested': {'leafkey': 'leafval'}})

            def setdefault(self):
                c = Config({'foo': 'bar', 'nested': {'leafkey': 'leafval'}})
                eq_(c.setdefault('foo'), 'bar')
                eq_(c.nested.setdefault('leafkey'), 'leafval')
                eq_(c.setdefault('notfoo', 'notbar'), 'notbar')
                eq_(c.notfoo, 'notbar')
                eq_(c.nested.setdefault('otherleaf', 'otherval'), 'otherval')
                eq_(c.nested.otherleaf, 'otherval')

            def update(self):
                c = Config(defaults={
                    'foo': 'bar',
                    'nested': {
                        'leafkey': 'leafval',
                    },
                })
                # Regular update(dict)
                c.update({'foo': 'notbar'})
                eq_(c.foo, 'notbar')
                c.nested.update({'leafkey': 'otherval'})
                eq_(c.nested.leafkey, 'otherval')
                # Apparently allowed but wholly useless
                c.update()
                eq_(c, {'foo': 'notbar', 'nested': {'leafkey': 'otherval'}})
                # Kwarg edition
                c.update(foo='otherbar')
                eq_(c.foo, 'otherbar')
                # Iterator of 2-tuples edition
                c.nested.update([
                    ('leafkey', 'yetanotherval'),
                    ('newleaf', 'turnt'),
                ])
                eq_(c.nested.leafkey, 'yetanotherval')
                eq_(c.nested.newleaf, 'turnt')

        def reinstatement_of_deleted_values_works_ok(self):
            # Sounds like a stupid thing to test, but when we have to track
            # deletions and mutations manually...it's an easy thing to overlook
            c = Config(defaults={'foo': 'bar'})
            eq_(c.foo, 'bar')
            del c['foo']
            # Sanity checks
            ok_('foo' not in c)
            eq_(len(c), 0)
            # Put it back again...as a different value, for funsies
            c.foo = 'formerly bar'
            # And make sure it stuck
            eq_(c.foo, 'formerly bar')

        def deleting_parent_keys_of_deleted_keys_subsumes_them(self):
            c = Config({'foo': {'bar': 'biz'}})
            del c.foo['bar']
            del c.foo
            # Make sure we didn't somehow still end up with {'foo': {'bar':
            # None}}
            eq_(c._deletions, {'foo': None})

        def supports_mutation_via_attribute_access(self):
            c = Config({'foo': 'bar'})
            eq_(c.foo, 'bar')
            c.foo = 'notbar'
            eq_(c.foo, 'notbar')
            eq_(c['foo'], 'notbar')

        def supports_nested_mutation_via_attribute_access(self):
            c = Config({'foo': {'bar': 'biz'}})
            eq_(c.foo.bar, 'biz')
            c.foo.bar = 'notbiz'
            eq_(c.foo.bar, 'notbiz')
            eq_(c['foo']['bar'], 'notbiz')

        def real_attrs_and_methods_win_over_attr_proxying(self):
            # Setup
            class MyConfig(Config):
                myattr = None
                def mymethod(self):
                    return 7
            c = MyConfig({'myattr': 'foo', 'mymethod': 'bar'})
            # By default, attr and config value separate
            eq_(c.myattr, None)
            eq_(c['myattr'], 'foo')
            # After a setattr, same holds true
            c.myattr = 'notfoo'
            eq_(c.myattr, 'notfoo')
            eq_(c['myattr'], 'foo')
            # Method and config value separate
            ok_(callable(c.mymethod))
            eq_(c.mymethod(), 7)
            eq_(c['mymethod'], 'bar')
            # And same after setattr
            def monkeys():
                return 13
            c.mymethod = monkeys
            eq_(c.mymethod(), 13)
            eq_(c['mymethod'], 'bar')

        def config_itself_stored_as_private_name(self):
            # I.e. one can refer to a key called 'config', which is relatively
            # commonplace (e.g. <Config>.myservice.config -> a config file
            # contents or path or etc)
            c = Config()
            c['foo'] = {'bar': 'baz'}
            c['whatever'] = {'config': 'myconfig'}
            eq_(c.foo.bar, 'baz')
            eq_(c.whatever.config, 'myconfig')

        def inherited_real_attrs_also_win_over_config_keys(self):
            class MyConfigParent(Config):
                parent_attr = 17
            class MyConfig(MyConfigParent):
                pass
            c = MyConfig()
            eq_(c.parent_attr, 17)
            c.parent_attr = 33
            oops = "Oops! Looks like config won over real attr!"
            ok_('parent_attr' not in c, oops)
            eq_(c.parent_attr, 33)
            c['parent_attr'] = 'fifteen'
            eq_(c.parent_attr, 33)
            eq_(c['parent_attr'], 'fifteen')

        def nonexistent_attrs_can_be_set_to_create_new_top_level_configs(self):
            # I.e. some_config.foo = 'bar' is like some_config['foo'] = 'bar'.
            # When this test breaks it usually means some_config.foo = 'bar'
            # sets a regular attribute - and the configuration itself is never
            # touched!
            c = Config()
            c.some_setting = 'some_value'
            eq_(c['some_setting'], 'some_value')

        def nonexistent_attr_setting_works_nested_too(self):
            c = Config()
            c.a_nest = {}
            eq_(c['a_nest'], {})
            c.a_nest.an_egg = True
            ok_(c['a_nest']['an_egg'] is True)

        def string_display(self):
            "__str__ and friends"
            config = Config(defaults={'foo': 'bar'})
            eq_(repr(config), "<Config: {'foo': 'bar'}>")

        def merging_does_not_wipe_user_modifications_or_deletions(self):
            c = Config({'foo': {'bar': 'biz'}, 'error': True})
            c.foo.bar = 'notbiz'
            del c['error']
            eq_(c['foo']['bar'], 'notbiz')
            ok_('error' not in c)
            c.merge()
            # Will be back to 'biz' if user changes don't get saved on their
            # own (previously they are just mutations on the cached central
            # config)
            eq_(c['foo']['bar'], 'notbiz')
            # And this would still be here, too
            ok_('error' not in c)

    class config_file_loading:
        "Configuration file loading"

        def system_global(self):
            "Systemwide conf files"
            for type_ in TYPES:
                config = _load('system_prefix', type_)
                eq_(config['outer']['inner']['hooray'], type_)

        def user_specific(self):
            "User-specific conf files"
            for type_ in TYPES:
                config = _load('user_prefix', type_)
                eq_(config['outer']['inner']['hooray'], type_)

        def project_specific(self):
            "Local-to-project conf files"
            for type_ in TYPES:
                c = Config(project_home=join(CONFIGS_PATH, type_))
                eq_(c.outer.inner.hooray, type_)

        def loads_no_project_specific_file_if_no_project_home_given(self):
            c = Config()
            eq_(c._project_path, None)
            eq_(list(c._project.keys()), [])
            defaults = ['tasks', 'run', 'runners', 'sudo']
            eq_(set(c.keys()), set(defaults))

        def honors_conf_file_flag(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'yaml', 'invoke.yaml'))
            eq_(c.outer.inner.hooray, 'yaml')

        @raises(UnknownFileType)
        def unknown_suffix_in_runtime_path_raises_useful_error(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'screw.ini'))
            eq_(c.boo, 'ini') # Should raise exception

        def python_modules_dont_load_special_vars(self):
            "Python modules don't load special vars"
            # Borrow another test's Python module.
            c = _load('system_prefix', 'python')
            # Sanity test that lowercase works
            eq_(c.outer.inner.hooray, 'python')
            # Real test that builtins, etc are stripped out
            for special in ('builtins', 'file', 'package', 'name', 'doc'):
                ok_('__{0}__'.format(special) not in c)


    class comparison_and_hashing:
        def comparison_looks_at_merged_config(self):
            c1 = Config(defaults={'foo': {'bar': 'biz'}})
            # Empty defaults to suppress global_defaults
            c2 = Config(defaults={}, overrides={'foo': {'bar': 'biz'}})
            ok_(c1 is not c2)
            ok_(c1._defaults != c2._defaults)
            eq_(c1, c2)

        def allows_comparison_with_real_dicts(self):
            c = Config({'foo': {'bar': 'biz'}})
            eq_(c['foo'], {'bar': 'biz'})

        @raises(TypeError)
        def is_explicitly_not_hashable(self):
            hash(Config())


    class env_vars:
        "Environment variables"
        def base_case_defaults_to_INVOKE_prefix(self):
            os.environ['INVOKE_FOO'] = 'bar'
            c = Config(defaults={'foo': 'notbar'})
            c.load_shell_env()
            eq_(c.foo, 'bar')

        def non_predeclared_settings_do_not_get_consumed(self):
            os.environ['INVOKE_HELLO'] = "is it me you're looking for?"
            c = Config()
            c.load_shell_env()
            ok_('HELLO' not in c)
            ok_('hello' not in c)

        def underscores_top_level(self):
            os.environ['INVOKE_FOO_BAR'] = 'biz'
            c = Config(defaults={'foo_bar': 'notbiz'})
            c.load_shell_env()
            eq_(c.foo_bar, 'biz')

        def underscores_nested(self):
            os.environ['INVOKE_FOO_BAR'] = 'biz'
            c = Config(defaults={'foo': {'bar': 'notbiz'}})
            c.load_shell_env()
            eq_(c.foo.bar, 'biz')

        def both_types_of_underscores_mixed(self):
            os.environ['INVOKE_FOO_BAR_BIZ'] = 'baz'
            c = Config(defaults={'foo_bar': {'biz': 'notbaz'}})
            c.load_shell_env()
            eq_(c.foo_bar.biz, 'baz')

        @raises(AmbiguousEnvVar)
        def ambiguous_underscores_dont_guess(self):
            os.environ['INVOKE_FOO_BAR'] = 'biz'
            c = Config(defaults={'foo_bar': 'wat', 'foo': {'bar': 'huh'}})
            c.load_shell_env()


        class type_casting:
            def strings_replaced_with_env_value(self):
                os.environ['INVOKE_FOO'] = six.u('myvalue')
                c = Config(defaults={'foo': 'myoldvalue'})
                c.load_shell_env()
                eq_(c.foo, six.u('myvalue'))
                ok_(isinstance(c.foo, six.text_type))

            def unicode_replaced_with_env_value(self):
                # Python 3 doesn't allow you to put 'bytes' objects into
                # os.environ, so the test makes no sense there.
                if six.PY3:
                    return
                os.environ['INVOKE_FOO'] = 'myunicode'
                c = Config(defaults={'foo': six.u('myoldvalue')})
                c.load_shell_env()
                eq_(c.foo, 'myunicode')
                ok_(isinstance(c.foo, str))

            def None_replaced(self):
                os.environ['INVOKE_FOO'] = 'something'
                c = Config(defaults={'foo': None})
                c.load_shell_env()
                eq_(c.foo, 'something')

            def booleans(self):
                for input_, result in (
                    ('0', False),
                    ('1', True),
                    ('', False),
                    ('meh', True),
                    ('false', True),
                ):
                    os.environ['INVOKE_FOO'] = input_
                    c = Config(defaults={'foo': bool()})
                    c.load_shell_env()
                    eq_(c.foo, result)

            def boolean_type_inputs_with_non_boolean_defaults(self):
                for input_ in ('0', '1', '', 'meh', 'false'):
                    os.environ['INVOKE_FOO'] = input_
                    c = Config(defaults={'foo': 'bar'})
                    c.load_shell_env()
                    eq_(c.foo, input_)

            def numeric_types_become_casted(self):
                tests = [
                    (int, '5', 5),
                    (float, '5.5', 5.5),
                    # TODO: more?
                ]
                # Can't use '5L' in Python 3, even having it in a branch makes
                # it upset.
                if not six.PY3:
                    tests.append((long, '5', long(5)))  # noqa
                for old, new_, result in tests:
                    os.environ['INVOKE_FOO'] = new_
                    c = Config(defaults={'foo': old()})
                    c.load_shell_env()
                    eq_(c.foo, result)

            def arbitrary_types_work_too(self):
                os.environ['INVOKE_FOO'] = 'whatever'
                class Meh(object):
                    def __init__(self, thing=None):
                        pass
                old_obj = Meh()
                c = Config(defaults={'foo': old_obj})
                c.load_shell_env()
                ok_(isinstance(c.foo, Meh))
                ok_(c.foo is not old_obj)


            class uncastable_types:
                @raises(UncastableEnvVar)
                def _uncastable_type(self, default):
                    os.environ['INVOKE_FOO'] = 'stuff'
                    c = Config(defaults={'foo': default})
                    c.load_shell_env()

                def lists(self):
                    self._uncastable_type(['a', 'list'])

                def tuples(self):
                    self._uncastable_type(('a', 'tuple'))


    class hierarchy:
        "Config hierarchy in effect"

        #
        # NOTE: most of these just leverage existing test fixtures (which live
        # in their own directories & have differing values for the 'hooray'
        # key), since we normally don't need more than 2-3 different file
        # locations for any one test.
        #

        def collection_overrides_defaults(self):
            c = Config(defaults={'nested': {'setting': 'default'}})
            c.load_collection({'nested': {'setting': 'collection'}})
            eq_(c.nested.setting, 'collection')

        def systemwide_overrides_collection(self):
            c = Config(system_prefix=join(CONFIGS_PATH, 'yaml/'))
            c.load_collection({'outer': {'inner': {'hooray': 'defaults'}}})
            eq_(c.outer.inner.hooray, 'yaml')

        def user_overrides_systemwide(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'yaml/'),
                user_prefix=join(CONFIGS_PATH, 'json/'),
            )
            eq_(c.outer.inner.hooray, 'json')

        def user_overrides_collection(self):
            c = Config(user_prefix=join(CONFIGS_PATH, 'json/'))
            c.load_collection({'outer': {'inner': {'hooray': 'defaults'}}})
            eq_(c.outer.inner.hooray, 'json')

        def project_overrides_user(self):
            c = Config(
                user_prefix=join(CONFIGS_PATH, 'json/'),
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            eq_(c.outer.inner.hooray, 'yaml')

        def project_overrides_systemwide(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'json/'),
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            eq_(c.outer.inner.hooray, 'yaml')

        def project_overrides_collection(self):
            c = Config(
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            c.load_collection({'outer': {'inner': {'hooray': 'defaults'}}})
            eq_(c.outer.inner.hooray, 'yaml')

        def env_vars_override_project(self):
            os.environ['INVOKE_OUTER_INNER_HOORAY'] = 'env'
            c = Config(
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            c.load_shell_env()
            eq_(c.outer.inner.hooray, 'env')

        def env_vars_override_user(self):
            os.environ['INVOKE_OUTER_INNER_HOORAY'] = 'env'
            c = Config(
                user_prefix=join(CONFIGS_PATH, 'yaml/'),
            )
            c.load_shell_env()
            eq_(c.outer.inner.hooray, 'env')

        def env_vars_override_systemwide(self):
            os.environ['INVOKE_OUTER_INNER_HOORAY'] = 'env'
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'yaml/'),
            )
            c.load_shell_env()
            eq_(c.outer.inner.hooray, 'env')

        def env_vars_override_collection(self):
            os.environ['INVOKE_OUTER_INNER_HOORAY'] = 'env'
            c = Config()
            c.load_collection({'outer': {'inner': {'hooray': 'defaults'}}})
            c.load_shell_env()
            eq_(c.outer.inner.hooray, 'env')

        def runtime_overrides_env_vars(self):
            os.environ['INVOKE_OUTER_INNER_HOORAY'] = 'env'
            c = Config(runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'))
            c.load_shell_env()
            eq_(c.outer.inner.hooray, 'json')

        def runtime_overrides_project(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'),
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            eq_(c.outer.inner.hooray, 'json')

        def runtime_overrides_user(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'),
                user_prefix=join(CONFIGS_PATH, 'yaml/'),
            )
            eq_(c.outer.inner.hooray, 'json')

        def runtime_overrides_systemwide(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'),
                system_prefix=join(CONFIGS_PATH, 'yaml/'),
            )
            eq_(c.outer.inner.hooray, 'json')

        def runtime_overrides_collection(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'))
            c.load_collection({'outer': {'inner': {'hooray': 'defaults'}}})
            eq_(c.outer.inner.hooray, 'json')

        def cli_overrides_override_all(self):
            "CLI-driven overrides win vs all other layers"
            # TODO: expand into more explicit tests like the above? meh
            c = Config(
                overrides={'outer': {'inner': {'hooray': 'overrides'}}},
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json')
            )
            eq_(c.outer.inner.hooray, 'overrides')

        def yaml_prevents_yml_json_or_python(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'all-four/'))
            ok_('json-only' not in c)
            ok_('python_only' not in c)
            ok_('yml-only' not in c)
            ok_('yaml-only' in c)
            eq_(c.shared, 'yaml-value')

        def yml_prevents_json_or_python(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'three-of-em/'))
            ok_('json-only' not in c)
            ok_('python_only' not in c)
            ok_('yml-only' in c)
            eq_(c.shared, 'yml-value')

        def json_prevents_python(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'json-and-python/'))
            ok_('python_only' not in c)
            ok_('json-only' in c)
            eq_(c.shared, 'json-value')


    class clone:
        def preserves_basic_members(self):
            c1 = Config(
                defaults={'key': 'default'},
                overrides={'key': 'override'},
                system_prefix='global',
                user_prefix='user',
                project_home='project',
                runtime_path='runtime.yaml',
            )
            c2 = c1.clone()
            # NOTE: expecting identical defaults also implicitly tests that
            # clone() passes in defaults= instead of doing an empty init +
            # copy. (When that is not the case, we end up with
            # global_defaults() being rerun and re-added to _defaults...)
            eq_(c2._defaults, c1._defaults)
            ok_(c2._defaults is not c1._defaults)
            eq_(c2._overrides, c1._overrides)
            ok_(c2._overrides is not c1._overrides)
            eq_(c2._system_prefix, c1._system_prefix)
            eq_(c2._user_prefix, c1._user_prefix)
            eq_(c2._project_home, c1._project_home)
            eq_(c2.prefix, c1.prefix)
            eq_(c2.file_prefix, c1.file_prefix)
            eq_(c2.env_prefix, c1.env_prefix)
            eq_(c2._runtime_path, c1._runtime_path)

        def preserves_merged_config(self):
            c = Config(
                defaults={'key': 'default'},
                overrides={'key': 'override'},
            )
            eq_(c.key, 'override')
            eq_(c._defaults['key'], 'default')
            c2 = c.clone()
            eq_(c2.key, 'override')
            eq_(c2._defaults['key'], 'default')
            eq_(c2._overrides['key'], 'override')

        def preserves_file_data(self):
            c = Config(system_prefix=join(CONFIGS_PATH, 'yaml/'))
            eq_(c.outer.inner.hooray, 'yaml')
            c2 = c.clone()
            eq_(c2.outer.inner.hooray, 'yaml')
            eq_(c2._system, {'outer': {'inner': {'hooray': 'yaml'}}})

        @patch.object(Config, '_load_yaml', return_value={
            'outer': {'inner': {'hooray': 'yaml'}}
        })
        def does_not_reload_file_data(self, load_yaml):
            path = join(CONFIGS_PATH, 'yaml/')
            c = Config(system_prefix=path)
            c2 = c.clone()
            eq_(c2.outer.inner.hooray, 'yaml')
            # Crummy way to say "only got called with this specific invocation
            # one time" (since assert_calls_with gets mad about other
            # invocations w/ different args)
            calls = load_yaml.call_args_list
            my_call = call("{0}invoke.yaml".format(path))
            try:
                calls.remove(my_call)
                ok_(my_call not in calls)
            except ValueError:
                err = "{0} not found in {1} even once!"
                assert False, err.format(my_call, calls)

        def preserves_env_data(self):
            os.environ['INVOKE_FOO'] = 'bar'
            c = Config(defaults={'foo': 'notbar'})
            c.load_shell_env()
            c2 = c.clone()
            eq_(c2.foo, 'bar')

        def works_correctly_when_subclassed(self):
            # Because sometimes, implementation #1 is really naive!
            class MyConfig(Config):
                pass
            c = MyConfig()
            ok_(isinstance(c, MyConfig)) # sanity
            c2 = c.clone()
            ok_(isinstance(c2, MyConfig)) # actual test

        def modified_config_data_is_present_during_post_init(self):
            # Scenario: subclass wants to honor config settings when doing
            # post-init stuff like loading additional config files (see eg
            # Fabric 2 + loading SSH config files).
            # This is enabled by splitting out the post-init step into its own
            # method & ensuring clone() only calls it at the very end.
            # Without that, a clone will exhibit default-level values (instead
            # of the source's final values) until the very end of clone().
            class MyConfig(Config):
                @staticmethod
                def global_defaults():
                    return dict(
                        Config.global_defaults(),
                        internal_setting='default!',
                    )

                def post_init(self):
                    super(MyConfig, self).post_init()
                    # Have to just record the visible value at time we're
                    # called, no other great way to notice something that ends
                    # up "correct" by end of clone()...!
                    self.recorded_internal_setting = self.internal_setting

            original = MyConfig()
            eq_(original.internal_setting, 'default!')
            original.internal_setting = 'custom!'
            clone = original.clone()
            eq_(clone.recorded_internal_setting, 'custom!')

        class into_kwarg:
            "'into' kwarg"
            def is_not_required(self):
                c = Config(defaults={'meh': 'okay'})
                c2 = c.clone()
                eq_(c2.meh, 'okay')

            def raises_TypeError_if_value_is_not_Config_subclass(self):
                try:
                    Config().clone(into=17)
                except TypeError:
                    pass
                else:
                    assert False, "Non-class obj did not raise TypeError!"

                class Foo(object):
                    pass

                try:
                    Config().clone(into=Foo)
                except TypeError:
                    pass
                else:
                    assert False, "Non-subclass did not raise TypeError!"

            def resulting_clones_are_typed_as_new_class(self):
                class MyConfig(Config):
                    pass
                c = Config()
                c2 = c.clone(into=MyConfig)
                ok_(type(c2) is MyConfig)

            def non_conflicting_values_are_merged(self):
                # NOTE: this is really just basic clone behavior.
                class MyConfig(Config):
                    @staticmethod
                    def global_defaults():
                        orig = Config.global_defaults()
                        orig['new'] = {'data': 'ohai'}
                        return orig
                c = Config(defaults={'other': {'data': 'hello'}})
                c['runtime'] = {'modification': 'sup'}
                c2 = c.clone(into=MyConfig)
                # New default data from MyConfig present
                eq_(c2.new.data, 'ohai')
                # As well as old default data from the cloned instance
                eq_(c2.other.data, 'hello')
                # And runtime user mods from the cloned instance
                eq_(c2.runtime.modification, 'sup')

        def does_not_deepcopy(self):
            c = Config(defaults={
                # Will merge_dicts happily
                'oh': {'dear': {'god': object()}},
                # And shallow-copy compound values
                'shallow': {'objects': ['copy', 'okay']},
                # Will preserve refrences to the innermost dict, sadly. Not
                # much we can do without incurring deepcopy problems (or
                # reimplementing it entirely)
                'welp': {'cannot': ['have', {'everything': 'we want'}]},
            })
            c2 = c.clone()
            # Basic identity
            ok_(c is not c2, "Clone had same identity as original!")
            # Dicts get recreated
            ok_(c.oh is not c2.oh, "Top level key had same identity!")
            ok_(c.oh.dear is not c2.oh.dear, "Midlevel key had same identity!")
            # Basic values get copied
            ok_(
                c.oh.dear.god is not c2.oh.dear.god,
                "Leaf object() had same identity!"
            )
            eq_(c.shallow.objects, c2.shallow.objects)
            ok_(
                c.shallow.objects is not c2.shallow.objects,
                "Shallow list had same identity!"
            )
            # Deeply nested non-dict objects are stil problematic, oh well
            ok_(
                c.welp.cannot[1] is c2.welp.cannot[1],
                "Huh, a deeply nested dict-in-a-list had different identity?"
            )
            ok_(
                c.welp.cannot[1]['everything'] is c2.welp.cannot[1]['everything'], # noqa
                "Huh, a deeply nested dict-in-a-list value had different identity?" # noqa
            )


    def can_be_pickled(self):
        c = Config(overrides={'foo': {'bar': {'biz': ['baz', 'buzz']}}})
        c2 = pickle.loads(pickle.dumps(c))
        eq_(c, c2)
        ok_(c is not c2)
        ok_(c.foo.bar.biz is not c2.foo.bar.biz)


# NOTE: merge_dicts has its own very low level unit tests in its own file
