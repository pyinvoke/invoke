from spec import Spec, skip, eq_

from invoke.config import Config


class Config_(Spec):
    class init:
        "__init__"

        def can_be_empty(self):
            skip()

        def configure_global_location_prefix(self):
            skip()

        def configure_user_location_prefix(self):
            skip()

        def unknown_kwargs_turn_into_top_level_defaults(self):
            skip()

    def can_update_config_adapters(self):
        # I.e. hand it a Defaults and a File and go to town
        skip()

    def allows_dict_and_attr_access(self):
        # TODO: combine with tests for Context probably
        skip()

    def nested_dict_values_also_allow_dual_access(self):
        # TODO: ditto
        skip()
