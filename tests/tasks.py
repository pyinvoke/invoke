from spec import Spec, skip, eq_, raises, ok_
from mock import Mock

from invoke import Context, Config, task, Task, Call
from invoke import FilesystemLoader as Loader

from _util import support


#
# NOTE: Most Task tests use @task as it's the primary interface and is a very
# thin wrapper around Task itself. This way we don't have to write 2x tests for
# both Task and @task. Meh :)
#

def _func(ctx):
    pass

class task_(Spec):
    "@task"

    def setup(self):
        self.loader = Loader(start=support)
        self.vanilla = self.loader.load('decorator')

    def allows_access_to_wrapped_object(self):
        def lolcats(ctx):
            pass
        eq_(task(lolcats).body, lolcats)

    def allows_alias_specification(self):
        eq_(self.vanilla['foo'], self.vanilla['bar'])

    def allows_multiple_aliases(self):
        eq_(self.vanilla['foo'], self.vanilla['otherbar'])

    def allows_default_specification(self):
        eq_(self.vanilla[''], self.vanilla['biz'])

    def has_autoprint_option(self):
        ap = self.loader.load('autoprint')
        eq_(ap['nope'].autoprint, False)
        eq_(ap['yup'].autoprint, True)

    @raises(ValueError)
    def raises_ValueError_on_multiple_defaults(self):
        self.loader.load('decorator_multi_default')

    def sets_arg_help(self):
        eq_(self.vanilla['punch'].help['why'], 'Motive')

    def sets_arg_kind(self):
        skip()

    def sets_which_args_are_optional(self):
        eq_(self.vanilla['optional_values'].optional, ('myopt',))

    def allows_annotating_args_as_positional(self):
        eq_(self.vanilla['one_positional'].positional, ['pos'])
        eq_(self.vanilla['two_positionals'].positional, ['pos1', 'pos2'])

    def when_positional_arg_missing_all_non_default_args_are_positional(self):
        eq_(self.vanilla['implicit_positionals'].positional, ['pos1', 'pos2'])

    def context_arguments_should_not_appear_in_implicit_positional_list(self):
        @task
        def mytask(ctx):
            pass
        eq_(len(mytask.positional), 0)

    def pre_tasks_stored_directly(self):
        @task
        def whatever(ctx):
            pass
        @task(pre=[whatever])
        def func(ctx):
            pass
        eq_(func.pre, [whatever])

    def allows_star_args_as_shortcut_for_pre(self):
        @task
        def pre1(ctx):
            pass
        @task
        def pre2(ctx):
            pass
        @task(pre1, pre2)
        def func(ctx):
            pass
        eq_(func.pre, (pre1, pre2))

    @raises(TypeError)
    def disallows_ambiguity_between_star_args_and_pre_kwarg(self):
        @task
        def pre1(ctx):
            pass
        @task
        def pre2(ctx):
            pass
        @task(pre1, pre=[pre2])
        def func(ctx):
            pass

    def sets_name(self):
        @task(name='foo')
        def bar(ctx):
            pass
        eq_(bar.name, 'foo')


class Task_(Spec):
    def has_useful_repr(self):
        i = repr(Task(_func))
        assert '_func' in i, "'func' not found in {0!r}".format(i)
        e = repr(Task(_func, name='funky'))
        assert 'funky' in e, "'funky' not found in {0!r}".format(e)
        assert '_func' not in e, "'_func' unexpectedly seen in {0!r}".format(e)

    def equality_testing(self):
        t1 = Task(_func, name='foo')
        t2 = Task(_func, name='foo')
        eq_(t1, t2)
        t3 = Task(_func, name='bar')
        assert t1 != t3

    class attributes:
        def has_default_flag(self):
            eq_(Task(_func).is_default, False)

        def name_defaults_to_body_name(self):
            eq_(Task(_func).name, '_func')

        def can_override_name(self):
            eq_(Task(_func, name='foo').name, 'foo')

    class callability:
        def setup(self):
            @task
            def foo(ctx):
                "My docstring"
                return 5
            self.task = foo

        def dunder_call_wraps_body_call(self):
            context = Context()
            eq_(self.task(context), 5)

        @raises(TypeError)
        def errors_if_first_arg_not_Context(self):
            @task
            def mytask(ctx):
                pass
            mytask(5)

        @raises(TypeError)
        def errors_if_no_first_arg_at_all(self):
            @task
            def mytask():
                pass

        def tracks_times_called(self):
            context = Context()
            eq_(self.task.called, False)
            self.task(context)
            eq_(self.task.called, True)
            eq_(self.task.times_called, 1)
            self.task(context)
            eq_(self.task.times_called, 2)

        def wraps_body_docstring(self):
            eq_(self.task.__doc__, "My docstring")

        def wraps_body_name(self):
            eq_(self.task.__name__, "foo")

    class get_arguments:
        def setup(self):
            @task(positional=['arg_3', 'arg1'], optional=['arg1'])
            def mytask(ctx, arg1, arg2=False, arg_3=5):
                pass
            self.task = mytask
            self.args = self.task.get_arguments()
            self.argdict = self._arglist_to_dict(self.args)

        def _arglist_to_dict(self, arglist):
            # This kinda duplicates Context.add_arg(x) for x in arglist :(
            ret = {}
            for arg in arglist:
                for name in arg.names:
                    ret[name] = arg
            return ret

        def _task_to_dict(self, task):
            return self._arglist_to_dict(task.get_arguments())

        def positional_args_come_first(self):
            eq_(self.args[0].name, 'arg_3')
            eq_(self.args[1].name, 'arg1')
            eq_(self.args[2].name, 'arg2')

        def kinds_are_preserved(self):
            eq_(
                [x.kind for x in self.args],
                # Remember that the default 'kind' is a string.
                [int, str, bool]
            )

        def positional_flag_is_preserved(self):
            eq_(
                [x.positional for x in self.args],
                [True, True, False]
            )

        def optional_flag_is_preserved(self):
            eq_(
                [x.optional for x in self.args],
                [False, True, False]
            )

        def optional_prevents_bool_defaults_from_affecting_kind(self):
            # Re #416. See notes in the function under test for rationale.
            @task(optional=['myarg'])
            def mytask(c, myarg=False):
                pass
            arg = mytask.get_arguments()[0]
            ok_(arg.kind is str) # not bool!

        def optional_plus_nonbool_default_does_not_override_kind(self):
            @task(optional=['myarg'])
            def mytask(c, myarg=17):
                pass
            arg = mytask.get_arguments()[0]
            ok_(arg.kind is int) # not str!

        def turns_function_signature_into_Arguments(self):
            eq_(len(self.args), 3, str(self.args))
            assert 'arg2' in self.argdict

        def shortflags_created_by_default(self):
            assert 'a' in self.argdict
            assert self.argdict['a'] is self.argdict['arg1']

        def shortflags_dont_care_about_positionals(self):
            "Positionalness doesn't impact whether shortflags are made"
            for short, long_ in (
                ('a', 'arg1'),
                ('r', 'arg2'),
                ('g', 'arg-3'),
            ):
                assert self.argdict[short] is self.argdict[long_]

        def autocreated_short_flags_can_be_disabled(self):
            @task(auto_shortflags=False)
            def mytask(ctx, arg):
                pass
            args = self._task_to_dict(mytask)
            assert 'a' not in args
            assert 'arg' in args

        def autocreated_shortflags_dont_collide(self):
            "auto-created short flags don't collide"
            @task
            def mytask(ctx, arg1, arg2, barg):
                pass
            args = self._task_to_dict(mytask)
            assert 'a' in args
            assert args['a'] is args['arg1']
            assert 'r' in args
            assert args['r'] is args['arg2']
            assert 'b' in args
            assert args['b'] is args['barg']

        def early_auto_shortflags_shouldnt_lock_out_real_shortflags(self):
            # I.e. "task --foo -f" => --foo should NOT get to pick '-f' for its
            # shortflag or '-f' is totally fucked.
            @task
            def mytask(ctx, longarg, l):
                pass
            args = self._task_to_dict(mytask)
            assert 'longarg' in args
            assert 'o' in args
            assert args['o'] is args['longarg']
            assert 'l' in args

        def context_arguments_are_not_returned(self):
            @task
            def mytask(ctx):
                pass
            eq_(len(mytask.get_arguments()), 0)

        def underscores_become_dashes(self):
            @task
            def mytask(ctx, longer_arg):
                pass
            arg = mytask.get_arguments()[0]
            eq_(arg.names, ('longer-arg', 'l'))
            eq_(arg.attr_name, 'longer_arg')
            eq_(arg.name, 'longer_arg')


# Dummy task for Call tests
_ = object()


class Call_(Spec):
    def setup(self):
        self.task = Task(Mock(__name__='mytask'))

    class init:
        class task:
            @raises(TypeError)
            def is_required(self):
                Call()

            def is_first_posarg(self):
                ok_(Call(_).task is _)

        class called_as:
            def defaults_to_None(self):
                eq_(Call(_).called_as, None)

            def may_be_given(self):
                eq_(Call(_, called_as='foo').called_as, 'foo')

        class args:
            def defaults_to_empty_tuple(self):
                eq_(Call(_).args, tuple())

            def may_be_given(self):
                eq_(Call(_, args=(1, 2, 3)).args, (1, 2, 3))

        class kwargs:
            def defaults_to_empty_dict(self):
                eq_(Call(_).kwargs, dict())

            def may_be_given(self):
                eq_(Call(_, kwargs={'foo': 'bar'}).kwargs, {'foo': 'bar'})

    class stringrep:
        "__str__"

        def includes_task_name(self):
            call = Call(self.task)
            eq_(str(call), "<Call 'mytask', args: (), kwargs: {}>")

        def includes_args_and_kwargs(self):
            call = Call(
                self.task,
                args=('posarg1', 'posarg2'),
                # Single-key dict to avoid dict ordering issues
                kwargs={'kwarg1': 'val1'},
            )
            eq_(str(call), "<Call 'mytask', args: ('posarg1', 'posarg2'), kwargs: {'kwarg1': 'val1'}>") # noqa

        def includes_aka_if_explicit_name_given(self):
            call = Call(self.task, called_as='notmytask')
            eq_(str(call), "<Call 'mytask' (called as: 'notmytask'), args: (), kwargs: {}>") # noqa

        def skips_aka_if_explicit_name_same_as_task_name(self):
            call = Call(self.task, called_as='mytask')
            eq_(str(call), "<Call 'mytask', args: (), kwargs: {}>")

    class make_context:
        @raises(TypeError)
        def requires_config_argument(self):
            Call(_).make_context()

        def creates_a_new_Context_from_given_config(self):
            conf = Config(defaults={'foo': 'bar'})
            ctx = Call(_).make_context(conf)
            ok_(isinstance(ctx, Context))
            eq_(ctx.foo, 'bar')

    class clone:
        def returns_new_but_equivalent_object(self):
            orig = Call(self.task)
            clone = orig.clone()
            ok_(clone is not orig)
            ok_(clone == orig)

        def can_clone_into_a_subclass(self):
            orig = Call(self.task)
            class MyCall(Call):
                pass
            clone = orig.clone(into=MyCall)
            eq_(clone, orig)
            ok_(isinstance(clone, MyCall))
