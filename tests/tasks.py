from spec import Spec, skip, eq_, raises

from invoke.tasks import task, Task
from invoke.loader import Loader

from _utils import support


#
# NOTE: Most Task tests use @task as it's the primary interface and is a very
# thin wrapper around Task itself. This way we don't have to write 2x tests for
# both Task and @task. Meh :)
#

class task_(Spec):
    "@task"

    def setup(self):
        self.loader = Loader(root=support)
        self.vanilla = self.loader.load_collection('decorator')

    def allows_access_to_wrapped_object(self):
        def lolcats():
            pass
        eq_(task(lolcats).body, lolcats)

    def allows_alias_specification(self):
        eq_(self.vanilla['foo'], self.vanilla['bar'])

    def allows_default_specification(self):
        eq_(self.vanilla[''], self.vanilla['biz'])

    @raises(ValueError)
    def raises_ValueError_on_multiple_defaults(self):
        self.loader.load_collection('decorator_multi_default')

    def sets_arg_help(self):
        eq_(self.vanilla['punch'].help['why'], 'Motive')

    def sets_arg_kind(self):
        skip()

    def allows_annotating_args_as_positional(self):
        eq_(self.vanilla['one_positional'].positional, ['pos'])
        eq_(self.vanilla['two_positionals'].positional, ['pos1', 'pos2'])

    def when_positional_arg_missing_all_non_default_args_are_positional(self):
        eq_(self.vanilla['implicit_positionals'].positional, ['pos1', 'pos2'])

    def pre_tasks_stored_as_simple_list_of_strings(self):
        @task(pre=['whatever'])
        def func():
            pass
        eq_(func.pre, ['whatever'])

    def allows_star_args_as_shortcut_for_pre(self):
        @task('my', 'pre', 'tasks')
        def func():
            pass
        eq_(func.pre, ('my', 'pre', 'tasks'))

    @raises(TypeError)
    def no_ambiguity_between_star_args_and_pre_kwarg(self):
        @task('lol', 'wut', pre=['no', 'wai'])
        def func():
            pass


class Task_(Spec):
    class get_arguments:
        def setup(self):
            @task(positional=['arg3', 'arg1'])
            def mytask(arg1, arg2=False, arg3=5):
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
            eq_(self.args[0].name, 'arg3')
            eq_(self.args[1].name, 'arg1')
            eq_(self.args[2].name, 'arg2')

        def kinds_are_preserved(self):
            eq_(
                map(lambda x: x.kind, self.args),
                # Remember that the default 'kind' is a string.
                [int, str, bool]
            )

        def positional_flag_is_preserved(self):
            eq_(
                map(lambda x: x.positional, self.args),
                [True, True, False]
            )

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
                ('g', 'arg3'),
            ):
                assert self.argdict[short] is self.argdict[long_]

        def autocreated_short_flags_can_be_disabled(self):
            @task(auto_shortflags=False)
            def mytask(arg):
                pass
            args = self._task_to_dict(mytask)
            assert 'a' not in args
            assert 'arg' in args

        def autocreated_shortflags_dont_collide(self):
            "auto-created short flags don't collide"
            @task
            def mytask(arg1, arg2, barg):
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
            def mytask(longarg, l):
                pass
            args = self._task_to_dict(mytask)
            assert 'longarg' in args
            assert 'o' in args
            assert args['o'] is args['longarg']
            assert 'l' in args
