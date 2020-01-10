import pickle
import os
from os.path import join, expanduser

from invoke.util import six
from mock import patch, call, Mock
import pytest
from pytest_relaxed import raises

from invoke.runners import Local
from invoke.config import Config
from invoke.exceptions import (
    AmbiguousEnvVar,
    UncastableEnvVar,
    UnknownFileType,
    UnpicklableConfigMember,
)

from _util import skip_if_windows, support


pytestmark = pytest.mark.usefixtures("integration")


CONFIGS_PATH = "configs"
TYPES = ("yaml", "yml", "json", "python")


def _load(kwarg, type_, **kwargs):
    path = join(CONFIGS_PATH, type_ + "/")
    kwargs[kwarg] = path
    return Config(**kwargs)


class Config_:
    class class_attrs:
        # TODO: move all other non-data-bearing kwargs to this mode
        class prefix:
            def defaults_to_invoke(self):
                assert Config().prefix == "invoke"

            @patch.object(Config, "_load_yaml")
            def informs_config_filenames(self, load_yaml):
                class MyConf(Config):
                    prefix = "other"

                MyConf(system_prefix="dir/")
                load_yaml.assert_any_call("dir/other.yaml")

            def informs_env_var_prefix(self):
                os.environ["OTHER_FOO"] = "bar"

                class MyConf(Config):
                    prefix = "other"

                c = MyConf(defaults={"foo": "notbar"})
                c.load_shell_env()
                assert c.foo == "bar"

        class file_prefix:
            def defaults_to_None(self):
                assert Config().file_prefix is None

            @patch.object(Config, "_load_yaml")
            def informs_config_filenames(self, load_yaml):
                class MyConf(Config):
                    file_prefix = "other"

                MyConf(system_prefix="dir/")
                load_yaml.assert_any_call("dir/other.yaml")

        class env_prefix:
            def defaults_to_None(self):
                assert Config().env_prefix is None

            def informs_env_vars_loaded(self):
                os.environ["OTHER_FOO"] = "bar"

                class MyConf(Config):
                    env_prefix = "other"

                c = MyConf(defaults={"foo": "notbar"})
                c.load_shell_env()
                assert c.foo == "bar"

    class global_defaults:
        @skip_if_windows
        def basic_settings(self):
            # Just a catchall for what the baseline config settings should
            # be...for some reason we're not actually capturing all of these
            # reliably (even if their defaults are often implied by the tests
            # which override them, e.g. runner tests around warn=True, etc).
            expected = {
                "run": {
                    "asynchronous": False,
                    "disown": False,
                    "dry": False,
                    "echo": False,
                    "echo_stdin": None,
                    "encoding": None,
                    "env": {},
                    "err_stream": None,
                    "fallback": True,
                    "hide": None,
                    "in_stream": None,
                    "out_stream": None,
                    "pty": False,
                    "replace_env": False,
                    "shell": "/bin/bash",
                    "warn": False,
                    "watchers": [],
                },
                "runners": {"local": Local},
                "sudo": {
                    "password": None,
                    "prompt": "[sudo] password: ",
                    "user": None,
                },
                "tasks": {
                    "auto_dash_names": True,
                    "collection_name": "tasks",
                    "dedupe": True,
                    "executor_class": None,
                    "search_root": None,
                },
                "timeouts": {"command": None},
            }
            assert Config.global_defaults() == expected

    class init:
        "__init__"

        def can_be_empty(self):
            assert Config().__class__ == Config  # derp

        @patch.object(Config, "_load_yaml")
        def configure_global_location_prefix(self, load_yaml):
            # This is a bit funky but more useful than just replicating the
            # same test farther down?
            Config(system_prefix="meh/")
            load_yaml.assert_any_call("meh/invoke.yaml")

        @skip_if_windows
        @patch.object(Config, "_load_yaml")
        def default_system_prefix_is_etc(self, load_yaml):
            # TODO: make this work on Windows somehow without being a total
            # tautology? heh.
            Config()
            load_yaml.assert_any_call("/etc/invoke.yaml")

        @patch.object(Config, "_load_yaml")
        def configure_user_location_prefix(self, load_yaml):
            Config(user_prefix="whatever/")
            load_yaml.assert_any_call("whatever/invoke.yaml")

        @patch.object(Config, "_load_yaml")
        def default_user_prefix_is_homedir_plus_dot(self, load_yaml):
            Config()
            load_yaml.assert_any_call(expanduser("~/.invoke.yaml"))

        @patch.object(Config, "_load_yaml")
        def configure_project_location(self, load_yaml):
            Config(project_location="someproject").load_project()
            load_yaml.assert_any_call(join("someproject", "invoke.yaml"))

        @patch.object(Config, "_load_yaml")
        def configure_runtime_path(self, load_yaml):
            Config(runtime_path="some/path.yaml").load_runtime()
            load_yaml.assert_any_call("some/path.yaml")

        def accepts_defaults_dict_kwarg(self):
            c = Config(defaults={"super": "low level"})
            assert c.super == "low level"

        def overrides_dict_is_first_posarg(self):
            c = Config({"new": "data", "run": {"hide": True}})
            assert c.run.hide is True  # default is False
            assert c.run.warn is False  # in global defaults, untouched
            assert c.new == "data"  # data only present at overrides layer

        def overrides_dict_is_also_a_kwarg(self):
            c = Config(overrides={"run": {"hide": True}})
            assert c.run.hide is True

        @patch.object(Config, "load_system")
        @patch.object(Config, "load_user")
        @patch.object(Config, "merge")
        def system_and_user_files_loaded_automatically(
            self, merge, load_u, load_s
        ):
            Config()
            load_s.assert_called_once_with(merge=False)
            load_u.assert_called_once_with(merge=False)
            merge.assert_called_once_with()

        @patch.object(Config, "load_system")
        @patch.object(Config, "load_user")
        def can_defer_loading_system_and_user_files(self, load_u, load_s):
            config = Config(lazy=True)
            assert not load_s.called
            assert not load_u.called
            # Make sure default levels are still in place! (When bug present,
            # i.e. merge() never called, config appears effectively empty.)
            assert config.run.echo is False

    class basic_API:
        "Basic API components"

        def can_be_used_directly_after_init(self):
            # No load() here...
            c = Config({"lots of these": "tests look similar"})
            assert c["lots of these"] == "tests look similar"

        def allows_dict_and_attr_access(self):
            # TODO: combine with tests for Context probably
            c = Config({"foo": "bar"})
            assert c.foo == "bar"
            assert c["foo"] == "bar"

        def nested_dict_values_also_allow_dual_access(self):
            # TODO: ditto
            c = Config({"foo": "bar", "biz": {"baz": "boz"}})
            # Sanity check - nested doesn't somehow kill simple top level
            assert c.foo == "bar"
            assert c["foo"] == "bar"
            # Actual check
            assert c.biz.baz == "boz"
            assert c["biz"]["baz"] == "boz"
            assert c.biz["baz"] == "boz"
            assert c["biz"].baz == "boz"

        def attr_access_has_useful_error_msg(self):
            c = Config()
            try:
                c.nope
            except AttributeError as e:
                expected = """
No attribute or config key found for 'nope'

Valid keys: ['run', 'runners', 'sudo', 'tasks', 'timeouts']

Valid real attributes: ['clear', 'clone', 'env_prefix', 'file_prefix', 'from_data', 'global_defaults', 'load_base_conf_files', 'load_collection', 'load_defaults', 'load_overrides', 'load_project', 'load_runtime', 'load_shell_env', 'load_system', 'load_user', 'merge', 'pop', 'popitem', 'prefix', 'set_project_location', 'set_runtime_path', 'setdefault', 'update']
""".strip()  # noqa
                assert str(e) == expected
            else:
                assert False, "Didn't get an AttributeError on bad key!"

        def subkeys_get_merged_not_overwritten(self):
            # Ensures nested keys merge deeply instead of shallowly.
            defaults = {"foo": {"bar": "baz"}}
            overrides = {"foo": {"notbar": "notbaz"}}
            c = Config(defaults=defaults, overrides=overrides)
            assert c.foo.notbar == "notbaz"
            assert c.foo.bar == "baz"

        def is_iterable_like_dict(self):
            c = Config(defaults={"a": 1, "b": 2})
            assert set(c.keys()) == {"a", "b"}
            assert set(list(c)) == {"a", "b"}

        def supports_readonly_dict_protocols(self):
            # Use single-keypair dict to avoid sorting problems in tests.
            c = Config(defaults={"foo": "bar"})
            c2 = Config(defaults={"foo": "bar"})
            assert "foo" in c
            assert "foo" in c2  # mostly just to trigger loading :x
            assert c == c2
            assert len(c) == 1
            assert c.get("foo") == "bar"
            if six.PY2:
                assert c.has_key("foo") is True  # noqa
                assert list(c.iterkeys()) == ["foo"]
                assert list(c.itervalues()) == ["bar"]
            assert list(c.items()) == [("foo", "bar")]
            assert list(six.iteritems(c)) == [("foo", "bar")]
            assert list(c.keys()) == ["foo"]
            assert list(c.values()) == ["bar"]

        class runtime_loading_of_defaults_and_overrides:
            def defaults_can_be_given_via_method(self):
                c = Config()
                assert "foo" not in c
                c.load_defaults({"foo": "bar"})
                assert c.foo == "bar"

            def defaults_can_skip_merging(self):
                c = Config()
                c.load_defaults({"foo": "bar"}, merge=False)
                assert "foo" not in c
                c.merge()
                assert c.foo == "bar"

            def overrides_can_be_given_via_method(self):
                c = Config(defaults={"foo": "bar"})
                assert c.foo == "bar"  # defaults level
                c.load_overrides({"foo": "notbar"})
                assert c.foo == "notbar"  # overrides level

            def overrides_can_skip_merging(self):
                c = Config()
                c.load_overrides({"foo": "bar"}, merge=False)
                assert "foo" not in c
                c.merge()
                assert c.foo == "bar"

        class deletion_methods:
            def pop(self):
                # Root
                c = Config(defaults={"foo": "bar"})
                assert c.pop("foo") == "bar"
                assert c == {}
                # With the default arg
                assert c.pop("wut", "fine then") == "fine then"
                # Leaf (different key to avoid AmbiguousMergeError)
                c.nested = {"leafkey": "leafval"}
                assert c.nested.pop("leafkey") == "leafval"
                assert c == {"nested": {}}

            def delitem(self):
                "__delitem__"
                c = Config(defaults={"foo": "bar"})
                del c["foo"]
                assert c == {}
                c.nested = {"leafkey": "leafval"}
                del c.nested["leafkey"]
                assert c == {"nested": {}}

            def delattr(self):
                "__delattr__"
                c = Config(defaults={"foo": "bar"})
                del c.foo
                assert c == {}
                c.nested = {"leafkey": "leafval"}
                del c.nested.leafkey
                assert c == {"nested": {}}

            def clear(self):
                c = Config(defaults={"foo": "bar"})
                c.clear()
                assert c == {}
                c.nested = {"leafkey": "leafval"}
                c.nested.clear()
                assert c == {"nested": {}}

            def popitem(self):
                c = Config(defaults={"foo": "bar"})
                assert c.popitem() == ("foo", "bar")
                assert c == {}
                c.nested = {"leafkey": "leafval"}
                assert c.nested.popitem() == ("leafkey", "leafval")
                assert c == {"nested": {}}

        class modification_methods:
            def setitem(self):
                c = Config(defaults={"foo": "bar"})
                c["foo"] = "notbar"
                assert c.foo == "notbar"
                del c["foo"]
                c["nested"] = {"leafkey": "leafval"}
                assert c == {"nested": {"leafkey": "leafval"}}

            def setdefault(self):
                c = Config({"foo": "bar", "nested": {"leafkey": "leafval"}})
                assert c.setdefault("foo") == "bar"
                assert c.nested.setdefault("leafkey") == "leafval"
                assert c.setdefault("notfoo", "notbar") == "notbar"
                assert c.notfoo == "notbar"
                nested = c.nested.setdefault("otherleaf", "otherval")
                assert nested == "otherval"
                assert c.nested.otherleaf == "otherval"

            def update(self):
                c = Config(
                    defaults={"foo": "bar", "nested": {"leafkey": "leafval"}}
                )
                # Regular update(dict)
                c.update({"foo": "notbar"})
                assert c.foo == "notbar"
                c.nested.update({"leafkey": "otherval"})
                assert c.nested.leafkey == "otherval"
                # Apparently allowed but wholly useless
                c.update()
                expected = {"foo": "notbar", "nested": {"leafkey": "otherval"}}
                assert c == expected
                # Kwarg edition
                c.update(foo="otherbar")
                assert c.foo == "otherbar"
                # Iterator of 2-tuples edition
                c.nested.update(
                    [("leafkey", "yetanotherval"), ("newleaf", "turnt")]
                )
                assert c.nested.leafkey == "yetanotherval"
                assert c.nested.newleaf == "turnt"

        def reinstatement_of_deleted_values_works_ok(self):
            # Sounds like a stupid thing to test, but when we have to track
            # deletions and mutations manually...it's an easy thing to overlook
            c = Config(defaults={"foo": "bar"})
            assert c.foo == "bar"
            del c["foo"]
            # Sanity checks
            assert "foo" not in c
            assert len(c) == 0
            # Put it back again...as a different value, for funsies
            c.foo = "formerly bar"
            # And make sure it stuck
            assert c.foo == "formerly bar"

        def deleting_parent_keys_of_deleted_keys_subsumes_them(self):
            c = Config({"foo": {"bar": "biz"}})
            del c.foo["bar"]
            del c.foo
            # Make sure we didn't somehow still end up with {'foo': {'bar':
            # None}}
            assert c._deletions == {"foo": None}

        def supports_mutation_via_attribute_access(self):
            c = Config({"foo": "bar"})
            assert c.foo == "bar"
            c.foo = "notbar"
            assert c.foo == "notbar"
            assert c["foo"] == "notbar"

        def supports_nested_mutation_via_attribute_access(self):
            c = Config({"foo": {"bar": "biz"}})
            assert c.foo.bar == "biz"
            c.foo.bar = "notbiz"
            assert c.foo.bar == "notbiz"
            assert c["foo"]["bar"] == "notbiz"

        def real_attrs_and_methods_win_over_attr_proxying(self):
            # Setup
            class MyConfig(Config):
                myattr = None

                def mymethod(self):
                    return 7

            c = MyConfig({"myattr": "foo", "mymethod": "bar"})
            # By default, attr and config value separate
            assert c.myattr is None
            assert c["myattr"] == "foo"
            # After a setattr, same holds true
            c.myattr = "notfoo"
            assert c.myattr == "notfoo"
            assert c["myattr"] == "foo"
            # Method and config value separate
            assert callable(c.mymethod)
            assert c.mymethod() == 7
            assert c["mymethod"] == "bar"
            # And same after setattr
            def monkeys():
                return 13

            c.mymethod = monkeys
            assert c.mymethod() == 13
            assert c["mymethod"] == "bar"

        def config_itself_stored_as_private_name(self):
            # I.e. one can refer to a key called 'config', which is relatively
            # commonplace (e.g. <Config>.myservice.config -> a config file
            # contents or path or etc)
            c = Config()
            c["foo"] = {"bar": "baz"}
            c["whatever"] = {"config": "myconfig"}
            assert c.foo.bar == "baz"
            assert c.whatever.config == "myconfig"

        def inherited_real_attrs_also_win_over_config_keys(self):
            class MyConfigParent(Config):
                parent_attr = 17

            class MyConfig(MyConfigParent):
                pass

            c = MyConfig()
            assert c.parent_attr == 17
            c.parent_attr = 33
            oops = "Oops! Looks like config won over real attr!"
            assert "parent_attr" not in c, oops
            assert c.parent_attr == 33
            c["parent_attr"] = "fifteen"
            assert c.parent_attr == 33
            assert c["parent_attr"] == "fifteen"

        def nonexistent_attrs_can_be_set_to_create_new_top_level_configs(self):
            # I.e. some_config.foo = 'bar' is like some_config['foo'] = 'bar'.
            # When this test breaks it usually means some_config.foo = 'bar'
            # sets a regular attribute - and the configuration itself is never
            # touched!
            c = Config()
            c.some_setting = "some_value"
            assert c["some_setting"] == "some_value"

        def nonexistent_attr_setting_works_nested_too(self):
            c = Config()
            c.a_nest = {}
            assert c["a_nest"] == {}
            c.a_nest.an_egg = True
            assert c["a_nest"]["an_egg"]

        def string_display(self):
            "__str__ and friends"
            config = Config(defaults={"foo": "bar"})
            assert repr(config) == "<Config: {'foo': 'bar'}>"

        def merging_does_not_wipe_user_modifications_or_deletions(self):
            c = Config({"foo": {"bar": "biz"}, "error": True})
            c.foo.bar = "notbiz"
            del c["error"]
            assert c["foo"]["bar"] == "notbiz"
            assert "error" not in c
            c.merge()
            # Will be back to 'biz' if user changes don't get saved on their
            # own (previously they are just mutations on the cached central
            # config)
            assert c["foo"]["bar"] == "notbiz"
            # And this would still be here, too
            assert "error" not in c

    class config_file_loading:
        "Configuration file loading"

        def system_global(self):
            "Systemwide conf files"
            # NOTE: using lazy=True to avoid autoloading so we can prove
            # load_system() works.
            for type_ in TYPES:
                config = _load("system_prefix", type_, lazy=True)
                assert "outer" not in config
                config.load_system()
                assert config.outer.inner.hooray == type_

        def system_can_skip_merging(self):
            config = _load("system_prefix", "yml", lazy=True)
            assert "outer" not in config._system
            assert "outer" not in config
            config.load_system(merge=False)
            # Test that we loaded into the per-level dict, but not the
            # central/merged config.
            assert "outer" in config._system
            assert "outer" not in config

        def user_specific(self):
            "User-specific conf files"
            # NOTE: using lazy=True to avoid autoloading so we can prove
            # load_user() works.
            for type_ in TYPES:
                config = _load("user_prefix", type_, lazy=True)
                assert "outer" not in config
                config.load_user()
                assert config.outer.inner.hooray == type_

        def user_can_skip_merging(self):
            config = _load("user_prefix", "yml", lazy=True)
            assert "outer" not in config._user
            assert "outer" not in config
            config.load_user(merge=False)
            # Test that we loaded into the per-level dict, but not the
            # central/merged config.
            assert "outer" in config._user
            assert "outer" not in config

        def project_specific(self):
            "Local-to-project conf files"
            for type_ in TYPES:
                c = Config(project_location=join(CONFIGS_PATH, type_))
                assert "outer" not in c
                c.load_project()
                assert c.outer.inner.hooray == type_

        def project_can_skip_merging(self):
            config = Config(
                project_location=join(CONFIGS_PATH, "yml"), lazy=True
            )
            assert "outer" not in config._project
            assert "outer" not in config
            config.load_project(merge=False)
            # Test that we loaded into the per-level dict, but not the
            # central/merged config.
            assert "outer" in config._project
            assert "outer" not in config

        def loads_no_project_specific_file_if_no_project_location_given(self):
            c = Config()
            assert c._project_path is None
            c.load_project()
            assert list(c._project.keys()) == []
            defaults = ["tasks", "run", "runners", "sudo", "timeouts"]
            assert set(c.keys()) == set(defaults)

        def project_location_can_be_set_after_init(self):
            c = Config()
            assert "outer" not in c
            c.set_project_location(join(CONFIGS_PATH, "yml"))
            c.load_project()
            assert c.outer.inner.hooray == "yml"

        def runtime_conf_via_cli_flag(self):
            c = Config(runtime_path=join(CONFIGS_PATH, "yaml", "invoke.yaml"))
            c.load_runtime()
            assert c.outer.inner.hooray == "yaml"

        def runtime_can_skip_merging(self):
            path = join(CONFIGS_PATH, "yaml", "invoke.yaml")
            config = Config(runtime_path=path, lazy=True)
            assert "outer" not in config._runtime
            assert "outer" not in config
            config.load_runtime(merge=False)
            # Test that we loaded into the per-level dict, but not the
            # central/merged config.
            assert "outer" in config._runtime
            assert "outer" not in config

        @raises(UnknownFileType)
        def unknown_suffix_in_runtime_path_raises_useful_error(self):
            c = Config(runtime_path=join(CONFIGS_PATH, "screw.ini"))
            c.load_runtime()

        def python_modules_dont_load_special_vars(self):
            "Python modules don't load special vars"
            # Borrow another test's Python module.
            c = _load("system_prefix", "python")
            # Sanity test that lowercase works
            assert c.outer.inner.hooray == "python"
            # Real test that builtins, etc are stripped out
            for special in ("builtins", "file", "package", "name", "doc"):
                assert "__{}__".format(special) not in c

        def python_modules_except_usefully_on_unpicklable_modules(self):
            # Re: #556; when bug present, a TypeError pops up instead (granted,
            # at merge time, but we want it to raise ASAP, so we're testing the
            # intended new behavior: raising at config load time.
            c = Config()
            c.set_runtime_path(join(support, "has_modules.py"))
            expected = r"'os' is a module.*giving a tasks file.*mistake"
            with pytest.raises(UnpicklableConfigMember, match=expected):
                c.load_runtime(merge=False)

        @patch("invoke.config.debug")
        def nonexistent_files_are_skipped_and_logged(self, mock_debug):
            c = Config()
            c._load_yml = Mock(side_effect=IOError(2, "aw nuts"))
            c.set_runtime_path("is-a.yml")  # Triggers use of _load_yml
            c.load_runtime()
            mock_debug.assert_any_call("Didn't see any is-a.yml, skipping.")

        @raises(IOError)
        def non_missing_file_IOErrors_are_raised(self):
            c = Config()
            c._load_yml = Mock(side_effect=IOError(17, "uh, what?"))
            c.set_runtime_path("is-a.yml")  # Triggers use of _load_yml
            c.load_runtime()

    class collection_level_config_loading:
        def performed_explicitly_and_directly(self):
            # TODO: do we want to update the other levels to allow 'direct'
            # loading like this, now that they all have explicit methods?
            c = Config()
            assert "foo" not in c
            c.load_collection({"foo": "bar"})
            assert c.foo == "bar"

        def merging_can_be_deferred(self):
            c = Config()
            assert "foo" not in c._collection
            assert "foo" not in c
            c.load_collection({"foo": "bar"}, merge=False)
            assert "foo" in c._collection
            assert "foo" not in c

    class comparison_and_hashing:
        def comparison_looks_at_merged_config(self):
            c1 = Config(defaults={"foo": {"bar": "biz"}})
            # Empty defaults to suppress global_defaults
            c2 = Config(defaults={}, overrides={"foo": {"bar": "biz"}})
            assert c1 is not c2
            assert c1._defaults != c2._defaults
            assert c1 == c2

        def allows_comparison_with_real_dicts(self):
            c = Config({"foo": {"bar": "biz"}})
            assert c["foo"] == {"bar": "biz"}

        @raises(TypeError)
        def is_explicitly_not_hashable(self):
            hash(Config())

    class env_vars:
        "Environment variables"

        def base_case_defaults_to_INVOKE_prefix(self):
            os.environ["INVOKE_FOO"] = "bar"
            c = Config(defaults={"foo": "notbar"})
            c.load_shell_env()
            assert c.foo == "bar"

        def non_predeclared_settings_do_not_get_consumed(self):
            os.environ["INVOKE_HELLO"] = "is it me you're looking for?"
            c = Config()
            c.load_shell_env()
            assert "HELLO" not in c
            assert "hello" not in c

        def underscores_top_level(self):
            os.environ["INVOKE_FOO_BAR"] = "biz"
            c = Config(defaults={"foo_bar": "notbiz"})
            c.load_shell_env()
            assert c.foo_bar == "biz"

        def underscores_nested(self):
            os.environ["INVOKE_FOO_BAR"] = "biz"
            c = Config(defaults={"foo": {"bar": "notbiz"}})
            c.load_shell_env()
            assert c.foo.bar == "biz"

        def both_types_of_underscores_mixed(self):
            os.environ["INVOKE_FOO_BAR_BIZ"] = "baz"
            c = Config(defaults={"foo_bar": {"biz": "notbaz"}})
            c.load_shell_env()
            assert c.foo_bar.biz == "baz"

        @raises(AmbiguousEnvVar)
        def ambiguous_underscores_dont_guess(self):
            os.environ["INVOKE_FOO_BAR"] = "biz"
            c = Config(defaults={"foo_bar": "wat", "foo": {"bar": "huh"}})
            c.load_shell_env()

        class type_casting:
            def strings_replaced_with_env_value(self):
                os.environ["INVOKE_FOO"] = u"myvalue"
                c = Config(defaults={"foo": "myoldvalue"})
                c.load_shell_env()
                assert c.foo == u"myvalue"
                assert isinstance(c.foo, six.text_type)

            def unicode_replaced_with_env_value(self):
                # Python 3 doesn't allow you to put 'bytes' objects into
                # os.environ, so the test makes no sense there.
                if six.PY3:
                    return
                os.environ["INVOKE_FOO"] = "myunicode"
                c = Config(defaults={"foo": u"myoldvalue"})
                c.load_shell_env()
                assert c.foo == "myunicode"
                assert isinstance(c.foo, str)

            def None_replaced(self):
                os.environ["INVOKE_FOO"] = "something"
                c = Config(defaults={"foo": None})
                c.load_shell_env()
                assert c.foo == "something"

            def booleans(self):
                for input_, result in (
                    ("0", False),
                    ("1", True),
                    ("", False),
                    ("meh", True),
                    ("false", True),
                ):
                    os.environ["INVOKE_FOO"] = input_
                    c = Config(defaults={"foo": bool()})
                    c.load_shell_env()
                    assert c.foo == result

            def boolean_type_inputs_with_non_boolean_defaults(self):
                for input_ in ("0", "1", "", "meh", "false"):
                    os.environ["INVOKE_FOO"] = input_
                    c = Config(defaults={"foo": "bar"})
                    c.load_shell_env()
                    assert c.foo == input_

            def numeric_types_become_casted(self):
                tests = [
                    (int, "5", 5),
                    (float, "5.5", 5.5),
                    # TODO: more?
                ]
                # Can't use '5L' in Python 3, even having it in a branch makes
                # it upset.
                if not six.PY3:
                    tests.append((long, "5", long(5)))  # noqa
                for old, new_, result in tests:
                    os.environ["INVOKE_FOO"] = new_
                    c = Config(defaults={"foo": old()})
                    c.load_shell_env()
                    assert c.foo == result

            def arbitrary_types_work_too(self):
                os.environ["INVOKE_FOO"] = "whatever"

                class Meh(object):
                    def __init__(self, thing=None):
                        pass

                old_obj = Meh()
                c = Config(defaults={"foo": old_obj})
                c.load_shell_env()
                assert isinstance(c.foo, Meh)
                assert c.foo is not old_obj

            class uncastable_types:
                @raises(UncastableEnvVar)
                def _uncastable_type(self, default):
                    os.environ["INVOKE_FOO"] = "stuff"
                    c = Config(defaults={"foo": default})
                    c.load_shell_env()

                def lists(self):
                    self._uncastable_type(["a", "list"])

                def tuples(self):
                    self._uncastable_type(("a", "tuple"))

    class hierarchy:
        "Config hierarchy in effect"

        #
        # NOTE: most of these just leverage existing test fixtures (which live
        # in their own directories & have differing values for the 'hooray'
        # key), since we normally don't need more than 2-3 different file
        # locations for any one test.
        #

        def collection_overrides_defaults(self):
            c = Config(defaults={"nested": {"setting": "default"}})
            c.load_collection({"nested": {"setting": "collection"}})
            assert c.nested.setting == "collection"

        def systemwide_overrides_collection(self):
            c = Config(system_prefix=join(CONFIGS_PATH, "yaml/"))
            c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
            assert c.outer.inner.hooray == "yaml"

        def user_overrides_systemwide(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, "yaml/"),
                user_prefix=join(CONFIGS_PATH, "json/"),
            )
            assert c.outer.inner.hooray == "json"

        def user_overrides_collection(self):
            c = Config(user_prefix=join(CONFIGS_PATH, "json/"))
            c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
            assert c.outer.inner.hooray == "json"

        def project_overrides_user(self):
            c = Config(
                user_prefix=join(CONFIGS_PATH, "json/"),
                project_location=join(CONFIGS_PATH, "yaml"),
            )
            c.load_project()
            assert c.outer.inner.hooray == "yaml"

        def project_overrides_systemwide(self):
            c = Config(
                system_prefix=join(CONFIGS_PATH, "json/"),
                project_location=join(CONFIGS_PATH, "yaml"),
            )
            c.load_project()
            assert c.outer.inner.hooray == "yaml"

        def project_overrides_collection(self):
            c = Config(project_location=join(CONFIGS_PATH, "yaml"))
            c.load_project()
            c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
            assert c.outer.inner.hooray == "yaml"

        def env_vars_override_project(self):
            os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
            c = Config(project_location=join(CONFIGS_PATH, "yaml"))
            c.load_project()
            c.load_shell_env()
            assert c.outer.inner.hooray == "env"

        def env_vars_override_user(self):
            os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
            c = Config(user_prefix=join(CONFIGS_PATH, "yaml/"))
            c.load_shell_env()
            assert c.outer.inner.hooray == "env"

        def env_vars_override_systemwide(self):
            os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
            c = Config(system_prefix=join(CONFIGS_PATH, "yaml/"))
            c.load_shell_env()
            assert c.outer.inner.hooray == "env"

        def env_vars_override_collection(self):
            os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
            c = Config()
            c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
            c.load_shell_env()
            assert c.outer.inner.hooray == "env"

        def runtime_overrides_env_vars(self):
            os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
            c = Config(runtime_path=join(CONFIGS_PATH, "json", "invoke.json"))
            c.load_runtime()
            c.load_shell_env()
            assert c.outer.inner.hooray == "json"

        def runtime_overrides_project(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
                project_location=join(CONFIGS_PATH, "yaml"),
            )
            c.load_runtime()
            c.load_project()
            assert c.outer.inner.hooray == "json"

        def runtime_overrides_user(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
                user_prefix=join(CONFIGS_PATH, "yaml/"),
            )
            c.load_runtime()
            assert c.outer.inner.hooray == "json"

        def runtime_overrides_systemwide(self):
            c = Config(
                runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
                system_prefix=join(CONFIGS_PATH, "yaml/"),
            )
            c.load_runtime()
            assert c.outer.inner.hooray == "json"

        def runtime_overrides_collection(self):
            c = Config(runtime_path=join(CONFIGS_PATH, "json", "invoke.json"))
            c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
            c.load_runtime()
            assert c.outer.inner.hooray == "json"

        def cli_overrides_override_all(self):
            "CLI-driven overrides win vs all other layers"
            # TODO: expand into more explicit tests like the above? meh
            c = Config(
                overrides={"outer": {"inner": {"hooray": "overrides"}}},
                runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
            )
            c.load_runtime()
            assert c.outer.inner.hooray == "overrides"

        def yaml_prevents_yml_json_or_python(self):
            c = Config(system_prefix=join(CONFIGS_PATH, "all-four/"))
            assert "json-only" not in c
            assert "python_only" not in c
            assert "yml-only" not in c
            assert "yaml-only" in c
            assert c.shared == "yaml-value"

        def yml_prevents_json_or_python(self):
            c = Config(system_prefix=join(CONFIGS_PATH, "three-of-em/"))
            assert "json-only" not in c
            assert "python_only" not in c
            assert "yml-only" in c
            assert c.shared == "yml-value"

        def json_prevents_python(self):
            c = Config(system_prefix=join(CONFIGS_PATH, "json-and-python/"))
            assert "python_only" not in c
            assert "json-only" in c
            assert c.shared == "json-value"

    class clone:
        def preserves_basic_members(self):
            c1 = Config(
                defaults={"key": "default"},
                overrides={"key": "override"},
                system_prefix="global",
                user_prefix="user",
                project_location="project",
                runtime_path="runtime.yaml",
            )
            c2 = c1.clone()
            # NOTE: expecting identical defaults also implicitly tests that
            # clone() passes in defaults= instead of doing an empty init +
            # copy. (When that is not the case, we end up with
            # global_defaults() being rerun and re-added to _defaults...)
            assert c2._defaults == c1._defaults
            assert c2._defaults is not c1._defaults
            assert c2._overrides == c1._overrides
            assert c2._overrides is not c1._overrides
            assert c2._system_prefix == c1._system_prefix
            assert c2._user_prefix == c1._user_prefix
            assert c2._project_prefix == c1._project_prefix
            assert c2.prefix == c1.prefix
            assert c2.file_prefix == c1.file_prefix
            assert c2.env_prefix == c1.env_prefix
            assert c2._runtime_path == c1._runtime_path

        def preserves_merged_config(self):
            c = Config(
                defaults={"key": "default"}, overrides={"key": "override"}
            )
            assert c.key == "override"
            assert c._defaults["key"] == "default"
            c2 = c.clone()
            assert c2.key == "override"
            assert c2._defaults["key"] == "default"
            assert c2._overrides["key"] == "override"

        def preserves_file_data(self):
            c = Config(system_prefix=join(CONFIGS_PATH, "yaml/"))
            assert c.outer.inner.hooray == "yaml"
            c2 = c.clone()
            assert c2.outer.inner.hooray == "yaml"
            assert c2._system == {"outer": {"inner": {"hooray": "yaml"}}}

        @patch.object(
            Config,
            "_load_yaml",
            return_value={"outer": {"inner": {"hooray": "yaml"}}},
        )
        def does_not_reload_file_data(self, load_yaml):
            path = join(CONFIGS_PATH, "yaml/")
            c = Config(system_prefix=path)
            c2 = c.clone()
            assert c2.outer.inner.hooray == "yaml"
            # Crummy way to say "only got called with this specific invocation
            # one time" (since assert_calls_with gets mad about other
            # invocations w/ different args)
            calls = load_yaml.call_args_list
            my_call = call("{}invoke.yaml".format(path))
            try:
                calls.remove(my_call)
                assert my_call not in calls
            except ValueError:
                err = "{} not found in {} even once!"
                assert False, err.format(my_call, calls)

        def preserves_env_data(self):
            os.environ["INVOKE_FOO"] = "bar"
            c = Config(defaults={"foo": "notbar"})
            c.load_shell_env()
            c2 = c.clone()
            assert c2.foo == "bar"

        def works_correctly_when_subclassed(self):
            # Because sometimes, implementation #1 is really naive!
            class MyConfig(Config):
                pass

            c = MyConfig()
            assert isinstance(c, MyConfig)  # sanity
            c2 = c.clone()
            assert isinstance(c2, MyConfig)  # actual test

        class into_kwarg:
            "'into' kwarg"

            def is_not_required(self):
                c = Config(defaults={"meh": "okay"})
                c2 = c.clone()
                assert c2.meh == "okay"

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
                assert type(c2) is MyConfig

            def non_conflicting_values_are_merged(self):
                # NOTE: this is really just basic clone behavior.
                class MyConfig(Config):
                    @staticmethod
                    def global_defaults():
                        orig = Config.global_defaults()
                        orig["new"] = {"data": "ohai"}
                        return orig

                c = Config(defaults={"other": {"data": "hello"}})
                c["runtime"] = {"modification": "sup"}
                c2 = c.clone(into=MyConfig)
                # New default data from MyConfig present
                assert c2.new.data == "ohai"
                # As well as old default data from the cloned instance
                assert c2.other.data == "hello"
                # And runtime user mods from the cloned instance
                assert c2.runtime.modification == "sup"

        def does_not_deepcopy(self):
            c = Config(
                defaults={
                    # Will merge_dicts happily
                    "oh": {"dear": {"god": object()}},
                    # And shallow-copy compound values
                    "shallow": {"objects": ["copy", "okay"]},
                    # Will preserve refrences to the innermost dict, sadly. Not
                    # much we can do without incurring deepcopy problems (or
                    # reimplementing it entirely)
                    "welp": {"cannot": ["have", {"everything": "we want"}]},
                }
            )
            c2 = c.clone()
            # Basic identity
            assert c is not c2, "Clone had same identity as original!"
            # Dicts get recreated
            assert c.oh is not c2.oh, "Top level key had same identity!"
            assert (
                c.oh.dear is not c2.oh.dear
            ), "Midlevel key had same identity!"  # noqa
            # Basic values get copied
            err = "Leaf object() had same identity!"
            assert c.oh.dear.god is not c2.oh.dear.god, err
            assert c.shallow.objects == c2.shallow.objects
            err = "Shallow list had same identity!"
            assert c.shallow.objects is not c2.shallow.objects, err
            # Deeply nested non-dict objects are stil problematic, oh well
            err = "Huh, a deeply nested dict-in-a-list had different identity?"
            assert c.welp.cannot[1] is c2.welp.cannot[1], err
            err = "Huh, a deeply nested dict-in-a-list value had different identity?"  # noqa
            assert (
                c.welp.cannot[1]["everything"]
                is c2.welp.cannot[1]["everything"]
            ), err  # noqa

    def can_be_pickled(self):
        c = Config(overrides={"foo": {"bar": {"biz": ["baz", "buzz"]}}})
        c2 = pickle.loads(pickle.dumps(c))
        assert c == c2
        assert c is not c2
        assert c.foo.bar.biz is not c2.foo.bar.biz


# NOTE: merge_dicts has its own very low level unit tests in its own file
