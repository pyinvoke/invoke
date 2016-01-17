import os
from os.path import join, expanduser

from spec import eq_, ok_, raises
from mock import patch, call

from invoke.config import Config
from invoke.exceptions import (
    AmbiguousEnvVar, UncastableEnvVar, UnknownFileType
)
from invoke.platform import DEFAULT_SYSTEM_PREFIX
from invoke.vendor import six

from _util import IntegrationSpec


CONFIGS_PATH = 'configs'
TYPES = ('yaml', 'json', 'python')

def _load(kwarg, type_):
    path = join(CONFIGS_PATH, type_, 'invoke')
    return Config(**{kwarg: path})

def _expect(where, type_, **kwargs):
    config = _load(where, type_)
    for key, value in six.iteritems(kwargs):
        eq_(config[key], value)


class Config_(IntegrationSpec):
    class init:
        "__init__"

        def can_be_empty(self):
            eq_(Config().__class__, Config) # derp

        @patch.object(Config, '_load_yaml')
        def configure_global_location_prefix(self, load_yaml):
            # This is a bit funky but more useful than just replicating the
            # same test farther down?
            Config(system_prefix='meh')
            load_yaml.assert_has_calls([call('meh.yaml')])

        @patch.object(Config, '_load_yaml')
        def default_system_prefix(self, load_yaml):
            Config()
            system_config_file = DEFAULT_SYSTEM_PREFIX + '.yaml'
            load_yaml.assert_has_calls([call(system_config_file)])

        @patch.object(Config, '_load_yaml')
        def configure_user_location_prefix(self, load_yaml):
            Config(user_prefix='whatever')
            load_yaml.assert_has_calls([call('whatever.yaml')])

        @patch.object(Config, '_load_yaml')
        def default_user_prefix_is_homedir(self, load_yaml):
            Config()
            load_yaml.assert_has_calls([call(expanduser('~/.invoke.yaml'))])

        @patch.object(Config, '_load_yaml')
        def configure_project_location(self, load_yaml):
            Config(project_home='someproject')
            # Use platform-agnostic relative path for project config file.
            project_config_file = os.path.join('someproject', 'invoke.yaml')
            load_yaml.assert_has_calls([call(project_config_file)])

        @patch.object(Config, '_load_yaml')
        def configure_runtime_path(self, load_yaml):
            Config(runtime_path='some/path.yaml')
            load_yaml.assert_has_calls([call('some/path.yaml')])

        def accepts_defaults_dict(self):
            c = Config(defaults={'super': 'low level'})
            eq_(c.super, 'low level')

        def defaults_dict_is_first_posarg(self):
            c = Config({'hi': 'there'})
            eq_(c.hi, 'there')

        def accepts_overrides_dict(self):
            c = Config(overrides={'I win': 'always'})
            eq_(c['I win'], 'always')

        def accepts_env_prefix_option(self):
            c = Config(env_prefix='INVOKE_')
            eq_(c._env_prefix, 'INVOKE_')


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

Valid keys: ['run', 'tasks']

Valid real attributes: ['clone', 'from_data', 'global_defaults', 'load_collection', 'load_files', 'load_shell_env', 'merge', 'paths']
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
            c = Config({'a': 1, 'b': 2})
            eq_(set(c.keys()), set(['a', 'b']))
            eq_(set(list(c)), set(['a', 'b']))

        def supports_readonly_dict_protocols(self):
            # Use single-keypair dict to avoid sorting problems in tests.
            c = Config({'foo': 'bar'})
            c2 = Config({'foo': 'bar'})
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

        def supports_mutation_dict_protocols(self):
            c = Config({'foo': 'bar'})
            eq_(len(c), 1)
            eq_(c.pop('foo'), 'bar')
            eq_(len(c), 0)
            c.setdefault('biz', 'baz')
            eq_(c['biz'], 'baz')
            c['boz'] = 'buzz'
            eq_(len(c), 2)
            del c['boz']
            eq_(len(c), 1)
            ok_('boz' not in c)
            eq_(c.popitem(), ('biz', 'baz'))
            eq_(len(c), 0)
            c.update({'foo': 'bar'})
            eq_(c['foo'], 'bar')

        def string_display(self):
            "__str__ and friends"
            config = Config({'foo': 'bar'})
            eq_(str(config), "<Config: {'foo': 'bar'}>")
            if six.PY2:
                eq_(unicode(config), six.u("<Config: {'foo': 'bar'}>"))  # noqa
            eq_(repr(config), "<Config: {'foo': 'bar'}>")


    class config_file_loading:
        "Configuration file loading"

        def system_global(self):
            "Systemwide conf files"
            for type_ in TYPES:
                _expect('system_prefix', type_, hooray=type_)

        def user_specific(self):
            "User-specific conf files"
            for type_ in TYPES:
                _expect('user_prefix', type_, hooray=type_)

        def project_specific(self):
            "Local-to-project conf files"
            for type_ in TYPES:
                c = Config(project_home=join(CONFIGS_PATH, type_))
                eq_(c.hooray, type_)

        def loads_no_project_specific_file_if_no_project_home_given(self):
            c = Config()
            eq_(c._project_path, None)
            eq_(list(c._project.keys()), [])
            eq_(set(c.keys()), set(['tasks', 'run'])) # defaults only

        def honors_conf_file_flag(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'yaml', 'invoke.yaml'))
            eq_(c.hooray, 'yaml')

        @raises(UnknownFileType)
        def unknown_suffix_in_runtime_path_raises_useful_error(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'screw.ini'))
            eq_(c.boo, 'ini') # Should raise exception

        def python_modules_dont_load_special_vars(self):
            "Python modules don't load special vars"
            # Borrow another test's Python module.
            c = _load('system_prefix', 'python')
            # Sanity test that lowercase works
            eq_(c.hooray, 'python')
            # Real test that builtins, etc are stripped out
            for special in ('builtins', 'file', 'package', 'name', 'doc'):
                ok_('__{0}__'.format(special) not in c)


    class env_vars:
        "Environment variables"
        def base_case(self):
            os.environ['FOO'] = 'bar'
            c = Config(defaults={'foo': 'notbar'})
            c.load_shell_env()
            eq_(c.foo, 'bar')

        def can_declare_prefix(self):
            os.environ['INVOKE_FOO'] = 'bar'
            c = Config({'foo': 'notbar'}, env_prefix='INVOKE_')
            c.load_shell_env()
            eq_(c.foo, 'bar')

        def non_predeclared_settings_do_not_get_consumed(self):
            os.environ['HELLO'] = "is it me you're looking for?"
            c = Config()
            c.load_shell_env()
            ok_('HELLO' not in c)
            ok_('hello' not in c)

        def underscores_top_level(self):
            os.environ['FOO_BAR'] = 'biz'
            c = Config(defaults={'foo_bar': 'notbiz'})
            c.load_shell_env()
            eq_(c.foo_bar, 'biz')

        def underscores_nested(self):
            os.environ['FOO_BAR'] = 'biz'
            c = Config(defaults={'foo': {'bar': 'notbiz'}})
            c.load_shell_env()
            eq_(c.foo.bar, 'biz')

        def both_types_of_underscores_mixed(self):
            os.environ['FOO_BAR_BIZ'] = 'baz'
            c = Config(defaults={'foo_bar': {'biz': 'notbaz'}})
            c.load_shell_env()
            eq_(c.foo_bar.biz, 'baz')

        @raises(AmbiguousEnvVar)
        def ambiguous_underscores_dont_guess(self):
            os.environ['FOO_BAR'] = 'biz'
            c = Config(defaults={'foo_bar': 'wat', 'foo': {'bar': 'huh'}})
            c.load_shell_env()


        class type_casting:
            def strings_replaced_with_env_value(self):
                os.environ['FOO'] = six.u('myvalue')
                c = Config(defaults={'foo': 'myoldvalue'})
                c.load_shell_env()
                eq_(c.foo, six.u('myvalue'))
                ok_(isinstance(c.foo, six.text_type))

            def unicode_replaced_with_env_value(self):
                # Python 3 doesn't allow you to put 'bytes' objects into
                # os.environ, so the test makes no sense there.
                if six.PY3:
                    return
                os.environ['FOO'] = 'myunicode'
                c = Config(defaults={'foo': six.u('myoldvalue')})
                c.load_shell_env()
                eq_(c.foo, 'myunicode')
                ok_(isinstance(c.foo, str))

            def None_replaced(self):
                os.environ['FOO'] = 'something'
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
                    os.environ['FOO'] = input_
                    c = Config(defaults={'foo': bool()})
                    c.load_shell_env()
                    eq_(c.foo, result)

            def boolean_type_inputs_with_non_boolean_defaults(self):
                for input_ in ('0', '1', '', 'meh', 'false'):
                    os.environ['FOO'] = input_
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
                    os.environ['FOO'] = new_
                    c = Config(defaults={'foo': old()})
                    c.load_shell_env()
                    eq_(c.foo, result)

            def arbitrary_types_work_too(self):
                os.environ['FOO'] = 'whatever'
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
                    os.environ['FOO'] = 'stuff'
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
            c = Config(defaults={'setting': 'default'})
            c.load_collection({'setting': 'collection'})
            eq_(c.setting, 'collection')

        def systemwide_overrides_collection(self):
            c = Config(system_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'))
            c.load_collection({'hooray': 'defaults'})
            eq_(c.hooray, 'yaml')

        def user_overrides_systemwide(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'),
                user_prefix=join(CONFIGS_PATH, 'json', 'invoke'),
            )
            eq_(c.hooray, 'json')

        def user_overrides_collection(self):
            c = Config(user_prefix=join(CONFIGS_PATH, 'json', 'invoke'))
            c.load_collection({'hooray': 'defaults'})
            eq_(c.hooray, 'json')

        def project_overrides_user(self):
            c = Config(
                user_prefix=join(CONFIGS_PATH, 'json', 'invoke'),
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            eq_(c.hooray, 'yaml')

        def project_overrides_systemwide(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'json', 'invoke'),
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            eq_(c.hooray, 'yaml')

        def project_overrides_collection(self):
            c = Config(
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            c.load_collection({'hooray': 'defaults'})
            eq_(c.hooray, 'yaml')

        def env_vars_override_project(self):
            os.environ['HOORAY'] = 'env'
            c = Config(
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            c.load_shell_env()
            eq_(c.hooray, 'env')

        def env_vars_override_user(self):
            os.environ['HOORAY'] = 'env'
            c = Config(
                user_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'),
            )
            c.load_shell_env()
            eq_(c.hooray, 'env')

        def env_vars_override_systemwide(self):
            os.environ['HOORAY'] = 'env'
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'),
            )
            c.load_shell_env()
            eq_(c.hooray, 'env')

        def env_vars_override_collection(self):
            os.environ['HOORAY'] = 'env'
            c = Config()
            c.load_collection({'hooray': 'defaults'})
            c.load_shell_env()
            eq_(c.hooray, 'env')

        def runtime_overrides_env_vars(self):
            os.environ['HOORAY'] = 'env'
            c = Config(runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'))
            c.load_shell_env()
            eq_(c.hooray, 'json')

        def runtime_overrides_project(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'),
                project_home=join(CONFIGS_PATH, 'yaml'),
            )
            eq_(c.hooray, 'json')

        def runtime_overrides_user(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'),
                user_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'),
            )
            eq_(c.hooray, 'json')

        def runtime_overrides_systemwide(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'),
                system_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'),
            )
            eq_(c.hooray, 'json')

        def runtime_overrides_collection(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json'))
            c.load_collection({'hooray': 'defaults'})
            eq_(c.hooray, 'json')

        def cli_overrides_override_all(self):
            "CLI-driven overrides win vs all other layers"
            # TODO: expand into more explicit tests like the above? meh
            c = Config(
                overrides={'hooray': 'overrides'},
                runtime_path=join(CONFIGS_PATH, 'json', 'invoke.json')
            )
            eq_(c.hooray, 'overrides')

        def yaml_prevents_json_or_python(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'all-three', 'invoke'))
            ok_('json-only' not in c)
            ok_('python_only' not in c)
            ok_('yaml-only' in c)
            eq_(c.shared, 'yaml-value')

        def json_prevents_python(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, 'json-and-python', 'invoke'))
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
                env_prefix='env',
                runtime_path='runtime.yaml',
            )
            c2 = c1.clone()
            eq_(c2._defaults, c1._defaults)
            ok_(c2._defaults is not c1._defaults)
            eq_(c2._overrides, c1._overrides)
            ok_(c2._overrides is not c1._overrides)
            eq_(c2._system_prefix, c1._system_prefix)
            eq_(c2._user_prefix, c1._user_prefix)
            eq_(c2._project_home, c1._project_home)
            eq_(c2._env_prefix, c1._env_prefix)
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
            c = Config(system_prefix=join(CONFIGS_PATH, 'yaml', 'invoke'))
            eq_(c.hooray, 'yaml')
            c2 = c.clone()
            eq_(c2.hooray, 'yaml')
            eq_(c2._system, {'hooray': 'yaml'})

        @patch.object(Config, '_load_yaml', return_value={'hooray': 'yaml'})
        def does_not_reload_file_data(self, load_yaml):
            path = join(CONFIGS_PATH, 'yaml', 'invoke')
            c = Config(system_prefix=path)
            c2 = c.clone()
            eq_(c2.hooray, 'yaml')
            # Crummy way to say "only got called with this specific invocation
            # one time" (since assert_calls_with gets mad about other
            # invocations w/ different args)
            calls = load_yaml.call_args_list
            my_call = call("{0}.yaml".format(path))
            calls.remove(my_call)
            ok_(my_call not in calls)

        def preserves_env_data(self):
            os.environ['FOO'] = 'bar'
            c = Config({'foo': 'notbar'})
            c.load_shell_env()
            c2 = c.clone()
            eq_(c2.foo, 'bar')
