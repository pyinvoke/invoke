import os
from os.path import join

from spec import Spec, skip, eq_, ok_, raises

from invoke.vendor.etcaetera.adapter import File, Adapter

from invoke.config import Config
from invoke.exceptions import AmbiguousEnvVar, UncastableEnvVar

from _utils import CleanEnvSpec


def _loads_path(c, path):
    files = [x for x in c.config.adapters if isinstance(x, File)]
    paths = [x.filepath for x in files]
    found = any(x == path for x in paths)
    ok_(found, "{0!r} not found, file adapters: {1!r}".format(path, paths))


CONFIGS_PATH = join('tests', '_support', 'configs')
TYPES = ('yaml', 'json', 'python')

def _load(kwarg, type_):
    path = join(CONFIGS_PATH, type_, 'invoke')
    c = Config(**{kwarg: path})
    c.load()
    return c

def _expect(where, type_, **kwargs):
    config = _load(where, type_)
    for key, value in kwargs.iteritems():
        eq_(config[key], value)


class Config_(CleanEnvSpec):
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
            eq_(len(c.config.adapters), 0)

        def accepts_overrides_dict(self):
            c = Config(overrides={'I win': 'always'})
            c.load()
            eq_(c['I win'], 'always')

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
                c = Config()
                c.load()
                eq_(c.keys(), [])

            def can_be_given_defaults_dict_arg(self):
                c = Config()
                c.load(defaults={'foo': 'bar'})
                eq_(c.foo, 'bar')

            def makes_data_available(self):
                c = Config(overrides={'foo': 'notbar'})
                ok_('foo' not in c.keys())
                c.load()
                ok_('foo' in c.keys())

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

        def string_display(self):
            "__str__ and friends"
            config = Config({'foo': 'bar'})
            config.load()
            eq_(str(config), "{'foo': 'bar'}")
            eq_(unicode(config), u"{'foo': 'bar'}")
            eq_(repr(config), "{'foo': 'bar'}")

    def python_modules_load_lowercase_but_not_special_vars(self):
        # Borrow another test's Python module.
        c = _load('global_prefix', 'python')
        # Sanity test that lowercase works
        eq_(c.hooray, 'python')
        # Real test that builtins, etc are stripped out
        for special in ('builtins', 'file', 'package', 'name', 'doc'):
            ok_('__{0}__'.format(special) not in c)

    class config_file_loading:
        "Configuration file loading"

        def system_global(self):
            "Systemwide conf files"
            for type_ in TYPES:
                _expect('global_prefix', type_, hooray=type_)

        def user_specific(self):
            "User-specific conf files"
            for type_ in TYPES:
                _expect('user_prefix', type_, hooray=type_)

        def project_specific(self):
            "Local-to-project conf files"
            for type_ in TYPES:
                c = Config(project_home=join(CONFIGS_PATH, type_))
                c.load()
                eq_(c.hooray, type_)

        def loads_no_project_specific_file_if_no_project_home_given(self):
            c = Config()
            c.load()
            eq_(c.keys(), [])

        def honors_conf_file_flag(self):
            c = Config(runtime_path=join(CONFIGS_PATH, 'yaml', 'invoke.yaml'))
            c.load()
            eq_(c.hooray, 'yaml')

    class env_vars:
        "Environment variables"
        def base_case(self):
            os.environ['FOO'] = 'bar'
            c = Config()
            c.load(defaults={'foo': 'notbar'})
            eq_(c.foo, 'bar')

        def non_predeclared_settings_do_not_get_consumed(self):
            os.environ['HELLO'] = "is it me you're looking for?"
            c = Config()
            c.load()
            ok_('HELLO' not in c)
            ok_('hello' not in c)

        def underscores_top_level(self):
            os.environ['FOO_BAR'] = 'biz'
            c = Config()
            c.load(defaults={'foo_bar': 'notbiz'})
            eq_(c.foo_bar, 'biz')

        def underscores_nested(self):
            os.environ['FOO_BAR'] = 'biz'
            c = Config()
            c.load(defaults={'foo': {'bar': 'notbiz'}})
            eq_(c.foo.bar, 'biz')

        def both_types_of_underscores_mixed(self):
            os.environ['FOO_BAR_BIZ'] = 'baz'
            c = Config()
            c.load(defaults={'foo_bar': {'biz': 'notbaz'}})
            eq_(c.foo_bar.biz, 'baz')

        @raises(AmbiguousEnvVar)
        def ambiguous_underscores_dont_guess(self):
            os.environ['FOO_BAR'] = 'biz'
            c = Config()
            c.load(defaults={'foo_bar': 'wat', 'foo': {'bar': 'huh'}})

        class type_casting:
            def strings_replaced_with_env_value(self):
                os.environ['FOO'] = u'myvalue'
                c = Config()
                c.load(defaults={'foo': 'myoldvalue'})
                eq_(c.foo, u'myvalue')
                ok_(isinstance(c.foo, unicode)) # FIXME: py3

            def unicode_replaced_with_env_value(self):
                os.environ['FOO'] = 'myunicode'
                c = Config()
                c.load(defaults={'foo': u'myoldvalue'})
                eq_(c.foo, 'myunicode')
                ok_(isinstance(c.foo, str)) # FIXME: py3

            def None_replaced(self):
                os.environ['FOO'] = 'something'
                c = Config()
                c.load(defaults={'foo': None})
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
                    c = Config()
                    c.load(defaults={'foo': bool()})
                    eq_(c.foo, result)

            def boolean_type_inputs_with_non_boolean_defaults(self):
                for input_ in ('0', '1', '', 'meh', 'false'):
                    os.environ['FOO'] = input_
                    c = Config()
                    c.load(defaults={'foo': 'bar'})
                    eq_(c.foo, input_)

            def numeric_types_become_casted(self):
                for old, new_, result in (
                    (int, '5', 5),
                    (float, '5.5', 5.5),
                    (long, '5', 5L),
                    # TODO: more?
                ):
                    os.environ['FOO'] = new_
                    c = Config()
                    c.load(defaults={'foo': old()})
                    eq_(c.foo, result)

            def arbitrary_types_work_too(self):
                os.environ['FOO'] = 'whatever'
                c = Config()
                class Meh(object):
                    def __init__(self, thing=None):
                        pass
                old_obj = Meh()
                c.load(defaults={'foo': old_obj})
                ok_(isinstance(c.foo, Meh))
                ok_(c.foo is not old_obj)

            class uncastable_types:
                @raises(UncastableEnvVar)
                def _uncastable_type(self, default):
                    os.environ['FOO'] = 'stuff'
                    c = Config()
                    c.load(defaults={'foo': default})

                def lists(self):
                    self._uncastable_type(['a', 'list'])

                def tuples(self):
                    self._uncastable_type(('a', 'tuple'))


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
