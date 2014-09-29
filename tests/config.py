from spec import Spec, skip, eq_, ok_

from invoke.vendor.etcaetera.adapter import File

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
            skip()

        def does_not_trigger_config_loading(self):
            skip()

    class basic_API:
        "Basic API components"

        def requires_explicit_loading(self):
            skip()

        def allows_modification_of_defaults(self):
            # Something light which wraps self._config.defaults[k] = v
            skip()

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

Valid real attributes: ['load']

Valid keys: []""".lstrip()
                eq_(str(e), expected)
            else:
                assert False, "Didn't get an AttributeError on bad key!"

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


