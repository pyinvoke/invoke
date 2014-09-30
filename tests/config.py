from spec import Spec, skip, eq_, ok_

from invoke.vendor.etcaetera.adapter import File, Adapter

from invoke.config import Config


def loads_path(c, path):
    files = [x for x in c._config.adapters if isinstance(x, File)]
    paths = [x.filepath for x in files]
    found = any(x == path for x in paths)
    ok_(found, "{0!r} not found, file adapters: {1!r}".format(path, paths))


class Config_(Spec):
    class init:
        "__init__"

        def can_be_empty(self):
            eq_(Config().__class__, Config) # derp

        def configure_global_location_prefix(self):
            # This is a bit funky but more useful than just replicating the
            # same test farther down?
            c = Config(global_prefix='meh')
            loads_path(c, 'meh.yaml')

        def default_global_prefix_is_etc(self):
            # TODO: make this work on Windows somehow without being a total
            # tautology? heh.
            c = Config()
            loads_path(c, '/etc/invoke.yaml')

        def configure_user_location_prefix(self):
            skip()

        def default_local_prefix_is_homedir(self):
            skip()

        def unknown_kwargs_turn_into_top_level_defaults(self):
            c = Config(foo='bar')
            eq_(c._config.defaults['foo'], 'bar')

        def accepts_explicit_adapter_override_list(self):
            c = Config(adapters=[])
            # Slightly encapsulation-breaking. Meh.
            # (Our) Config objs always start with a Defaults.
            eq_(len(c._config.adapters), 1)

        def does_not_trigger_config_loading(self):
            # Cuz automatic loading could potentially be surprising.
            # Meh-tastic no-exception-raised test.
            class DummyAdapter(Adapter):
                def load(self, *args, **kwargs):
                    raise Exception("I shouldn't have been called!")
            c = Config(adapters=[DummyAdapter()])

    class basic_API:
        "Basic API components"

        def load_method_is_an_thing(self):
            # Kinda duplicative but meh, nice and explicit.
            c = Config(default='value')
            c.load()
            eq_(c.default, 'value')

        def can_set_defaults_after_initialization(self):
            # Something light which wraps self._config.defaults[k] = v
            c = Config()
            c.set_defaults({'foo': 'bar'})
            c.load()
            eq_(c.foo, 'bar')

        def set_defaults_overrides_convenience_kwargs(self):
            c = Config(foo='bar')
            c.set_defaults({'biz': 'baz'})
            c.load()
            ok_('foo' not in c, "Expected {0!r} not to include 'foo'!")
            ok_('biz' in c, "Expected {0!r} to include 'biz'!")

        def allows_dict_and_attr_access(self):
            # TODO: combine with tests for Context probably
            skip()

        def nested_dict_values_also_allow_dual_access(self):
            # TODO: ditto
            skip()

        def attr_access_has_useful_errr_msg(self):
            c = Config()
            c.load()
            try:
                c.nope
            except AttributeError as e:
                expected = """
No attribute or config key found for 'nope'

Valid real attributes: ['keys', 'load', 'set_defaults']

Valid keys: []""".lstrip()
                eq_(str(e), expected)
            else:
                assert False, "Didn't get an AttributeError on bad key!"

        def loaded_keys_are_not_case_munged(self):
            # Looks tautological, but ensures we're suppressing etcaetera's
            # default UPPERCASE_EVERYTHING behavior
            d = {'FOO': 'bar', 'biz': 'baz', 'Boz': 'buzz'}
            c = Config(**d)
            c.load()
            for x in d:
                err = "Expected to find {0!r} in {1!r}, didn't"
                ok_(x in c, err.format(x, c.keys()))

        def is_iterable_like_dict(self):
            def expect(c, expected):
                eq_(set(c.keys()), expected)
                eq_(set(list(c)), expected)
            c = Config(a=1, b=2)
            expect(c, set())
            c.load()
            expect(c, set(['a', 'b']))

        def supports_membership_testing_like_dict(self):
            c = Config(foo='bar')
            c.load()
            ok_('foo' in c, "Unable to find 'foo' in {0!r}".format(c))

    class system_global:
        "Systemwide conf file"
        def yaml_first(self):
            c = Config(global_prefix='tests/_support/configs/global')
            c.load()
            eq_(c.hooray, 'configuration')

        def json_if_no_yaml(self):
            skip()

        def python_if_no_json_or_yaml(self):
            skip()

    class user_specific:
        "User-specific conf file"
        def yaml_first(self):
            skip()

        def json_if_no_yaml(self):
            skip()

        def python_if_no_json_or_yaml(self):
            skip()

    class project_specific:
        "Local-to-project conf file"
        def yaml_first(self):
            skip()

        def json_if_no_yaml(self):
            skip()

        def python_if_no_json_or_yaml(self):
            skip()

    def honors_conf_file_flag(self):
        skip()

    class env_vars:
        "Environment variables"
        def base_case(self):
            # FOO=bar
            skip()

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


