import os
from os.path import join

from spec import Spec, skip, eq_, ok_

from invoke.vendor.etcaetera.adapter import File, Adapter

from invoke.config import Config


def _loads_path(c, path):
    files = [x for x in c.config.adapters if isinstance(x, File)]
    paths = [x.filepath for x in files]
    found = any(x == path for x in paths)
    ok_(found, "{0!r} not found, file adapters: {1!r}".format(path, paths))

CONFIGS_PATH = join('tests', '_support', 'configs')

def _load(key, path):
    path = join(CONFIGS_PATH, key, path)
    c = Config(**{'{0}_prefix'.format(key): path})
    c.load()
    return c


class Config_(Spec):
    class init:
        "__init__"

        def can_be_empty(self):
            eq_(Config().__class__, Config) # derp

        def configure_global_location_prefix(self):
            # This is a bit funky but more useful than just replicating the
            # same test farther down?
            c = Config(global_prefix='meh')
            _loads_path(c, 'meh.yaml')

        def default_global_prefix_is_etc(self):
            # TODO: make this work on Windows somehow without being a total
            # tautology? heh.
            _loads_path(Config(), '/etc/invoke.yaml')

        def configure_user_location_prefix(self):
            c = Config(user_prefix='whatever')
            _loads_path(c, 'whatever.yaml')

        def default_user_prefix_is_homedir(self):
            _loads_path(Config(), '~/.invoke.yaml')

        def configure_project_location(self):
            c = Config(project_home='someproject')
            _loads_path(c, 'someproject/invoke.yaml')

        def configure_runtime_path(self):
            c = Config(runtime_path='some/path.yaml')
            _loads_path(c, 'some/path.yaml')

        def accepts_explicit_adapter_override_list(self):
            c = Config(adapters=[])
            # Slightly encapsulation-breaking. Meh.
            # (Our) Config objs always start with a Defaults.
            eq_(len(c.config.adapters), 1)

        def accepts_overrides_dict(self):
            skip()

        def does_not_trigger_config_loading(self):
            # Cuz automatic loading could potentially be surprising.
            # Meh-tastic no-exception-raised test.
            class DummyAdapter(Adapter):
                def load(self, *args, **kwargs):
                    raise Exception("I shouldn't have been called!")
            c = Config(adapters=[DummyAdapter()])

    class basic_API:
        "Basic API components"

        class load:
            "load()"
            # TODO: rename?
            def can_be_called_empty(self):
                skip()

            def can_be_given_defaults_dict_arg(self):
                skip()

            def makes_data_available(self):
                skip()

        def allows_dict_and_attr_access(self):
            # TODO: combine with tests for Context probably
            c = Config({'foo': 'bar'})
            c.load()
            eq_(c.foo, 'bar')
            eq_(c['foo'], 'bar')

        def nested_dict_values_also_allow_dual_access(self):
            # TODO: ditto
            c = Config({'foo': 'bar', 'biz': {'baz': 'boz'}})
            c.load()
            # Sanity check - nested doesn't somehow kill simple top level
            eq_(c.foo, 'bar')
            eq_(c['foo'], 'bar')
            # Actual check
            eq_(c.biz.baz, 'boz')
            eq_(c['biz']['baz'], 'boz')
            eq_(c.biz['baz'], 'boz')
            eq_(c['biz'].baz, 'boz')

        def attr_access_has_useful_errr_msg(self):
            c = Config()
            c.load()
            try:
                c.nope
            except AttributeError as e:
                expected = """
No attribute or config key found for 'nope'

Valid real attributes: ['clone', 'from_data', 'load']

Valid keys: []""".lstrip()
                eq_(str(e), expected)
            else:
                assert False, "Didn't get an AttributeError on bad key!"

        def loaded_keys_are_not_case_munged(self):
            # Looks tautological, but ensures we're suppressing etcaetera's
            # default UPPERCASE_EVERYTHING behavior
            d = {'FOO': 'bar', 'biz': 'baz', 'Boz': 'buzz'}
            c = Config(d)
            c.load()
            for x in d:
                err = "Expected to find {0!r} in {1!r}, didn't"
                ok_(x in c, err.format(x, c.keys()))

        def is_iterable_like_dict(self):
            def expect(c, expected):
                eq_(set(c.keys()), expected)
                eq_(set(list(c)), expected)
            c = Config({'a': 1, 'b': 2})
            expect(c, set())
            c.load()
            expect(c, set(['a', 'b']))

        def supports_readonly_dict_protocols(self):
            # Use single-keypair dict to avoid sorting problems in tests.
            c = Config({'foo': 'bar'})
            c2 = Config({'foo': 'bar'})
            c.load()
            c2.load()
            ok_('foo' in c)
            eq_(c, c2)
            eq_(len(c), 1)
            eq_(c.get('foo'), 'bar')
            eq_(c.has_key('foo'), True)
            eq_(c.items(), [('foo', 'bar')])
            eq_(list(c.iteritems()), [('foo', 'bar')])
            eq_(list(c.iterkeys()), ['foo'])
            eq_(list(c.itervalues()), ['bar'])
            eq_(c.keys(), ['foo'])
            eq_(c.values(), ['bar'])

        def supports_mutation_dict_protocols(self):
            c = Config({'foo': 'bar'})
            c.load()
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

    class system_global:
        "Systemwide conf file"
        def yaml_first(self):
            c = _load('global', join('yaml-only', 'invoke'))
            eq_(c.hooray, 'yaml')

        def json_if_no_yaml(self):
            c = _load('global', join('json-only', 'invoke'))
            eq_(c.hooray, 'json')

        def python_if_no_json_or_yaml(self):
            c = _load('global', join('python-only', 'invoke'))
            eq_(c.hooray, 'python')

    class user_specific:
        "User-specific conf file"
        def yaml_first(self):
            c = _load('user', join('yaml-only', '.invoke'))
            eq_(c.user, 'yaml')

        def json_if_no_yaml(self):
            c = _load('user', join('json-only', '.invoke'))
            eq_(c.user, 'json')

        def python_if_no_json_or_yaml(self):
            c = _load('user', join('python-only', '.invoke'))
            eq_(c.user, 'python')

    class project_specific:
        "Local-to-project conf file"
        def yaml_first(self):
            c = Config(project_home=join(CONFIGS_PATH, 'project', 'yaml-only'))
            c.load()
            eq_(c.project_setting, 'yaml')

        def json_if_no_yaml(self):
            c = Config(project_home=join(CONFIGS_PATH, 'project', 'json-only'))
            c.load()
            eq_(c.project_setting, 'json')

        def python_if_no_json_or_yaml(self):
            c = Config(project_home=join(CONFIGS_PATH, 'project', 'py-only'))
            c.load()
            eq_(c.project_setting, 'python')

        def loads_nothing_if_no_project_home_given(self):
            c = Config()
            c.load()
            eq_(c.keys(), [])

    def honors_conf_file_flag(self):
        c = Config(runtime_path=join(CONFIGS_PATH, 'runtime', 'runtime.yaml'))
        c.load()
        eq_(c["what time?"], "run time!")

    class env_vars:
        "Environment variables"
        def base_case(self):
            # FOO=bar
            c = Config({'foo': 'notbar'})
            os.environ['FOO'] = 'bar'
            c.load()
            eq_(c.foo, 'bar')

        def throws_error_on_undefined_settings(self):
            skip()

        def underscores_top_level(self):
            # FOO_BAR=biz => {'foo_bar': 'biz'}
            skip()

        def underscores_nested(self):
            # FOO_BAR=biz => {'foo': {'bar': 'biz'}}
            skip()

        def both_underscores(self):
            # FOO_BAR_BIZ=baz => {'foo_bar': {'biz': 'baz'}}
            skip()

    class hierarchy:
        "Config hierarchy in effect"
        def systemwide_overrides_collection(self):
            skip()

        def user_overrides_systemwide(self):
            skip()

        def user_overrides_collection(self):
            skip()

        def project_overrides_user(self):
            skip()

        def project_overrides_systemwide(self):
            skip()

        def project_overrides_collection(self):
            skip()

        def env_vars_override_project(self):
            skip()

        def env_vars_override_user(self):
            skip()

        def env_vars_override_systemwide(self):
            skip()

        def env_vars_override_collection(self):
            skip()

        def runtime_overrides_env_vars(self):
            skip()

        def runtime_overrides_project(self):
            skip()

        def runtime_overrides_user(self):
            skip()

        def runtime_overrides_systemwide(self):
            skip()

        def runtime_overrides_collection(self):
            skip()

        def e_flag_overrides_all(self):
            "-e overrides run.echo for all other layers"
            skip()


    class clone:
        def setup(self):
            self.c = Config({'foo': {'bar': {'biz': ['baz']}}})

        def load_before_and_after(self):
            c = self.c
            c.load()
            c2 = c.clone()
            c2.load()
            eq_(c, c2)
            ok_(c is not c2)
            ok_(c.config is not c2.config)
            eq_(c.foo.bar.biz, c2.foo.bar.biz)
            ok_(c.foo.bar.biz is not c2.foo.bar.biz)

        def no_loading_at_all(self):
            c = self.c
            c2 = c.clone()
            eq_(c, c2)
            ok_(c is not c2)
            ok_(c.config is not c2.config)
            # Unloaded -> looks empty
            eq_(c.keys(), [])
            eq_(c2.keys(), [])

        def load_after_only(self):
            c = self.c
            c2 = c.clone()
            c2.load()
            eq_(c2.foo.bar.biz, ['baz'])
