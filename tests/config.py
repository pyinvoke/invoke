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
            # same test in Executor?
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
