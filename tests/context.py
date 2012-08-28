import copy

from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument, Context
from invoke.task import task
from invoke.collection import Collection


class Context_(Spec):
    def may_have_a_name(self):
        c = Context(name='taskname')
        eq_(c.name, 'taskname')

    def may_have_aliases(self):
        c = Context(name='realname', aliases=('othername', 'yup'))
        assert 'othername' in c.aliases

    def may_give_arg_list_at_init_time(self):
        a1 = Argument('foo')
        a2 = Argument('bar')
        c = Context(name='name', args=(a1, a2))
        assert c.args['foo'] is a1

    class add_arg:
        def setup(self):
            self.c = Context()

        def can_take_Argument_instance(self):
            a = Argument(names=('foo',))
            self.c.add_arg(a)
            assert self.c.args['foo'] is a

        def can_take_name_arg(self):
            self.c.add_arg('foo')
            assert 'foo' in self.c.args

        def can_take_kwargs(self):
            self.c.add_arg(names=('foo', 'bar'))
            assert 'foo' in self.c.args and 'bar' in self.c.args

        @raises(ValueError)
        def raises_ValueError_on_duplicate(self):
            self.c.add_arg(names=('foo', 'bar'))
            self.c.add_arg(name='bar')

        def adds_flaglike_name_to_dot_flags(self):
            "adds flaglike name to .flags"
            self.c.add_arg('foo')
            assert '--foo' in self.c.flags

        def adds_all_names_to_dot_flags(self):
            "adds all names to .flags"
            self.c.add_arg(names=('foo', 'bar'))
            assert '--foo' in self.c.flags
            assert '--bar' in self.c.flags

        def turns_single_character_names_into_short_flags(self):
            self.c.add_arg('f')
            assert '-f' in self.c.flags
            assert '--f' not in self.c.flags

    class deepcopy:
        "__deepcopy__"
        def setup(self):
            self.arg = Argument('--boolean')
            self.orig = Context(
                name='mytask',
                args=(self.arg,),
                aliases=('othername',)
            )
            self.new = copy.deepcopy(self.orig)

        def returns_correct_copy(self):
            assert self.new is not self.orig
            eq_(self.new.name, 'mytask')
            assert 'othername' in self.new.aliases

        def includes_arguments(self):
            eq_(len(self.new.args), 1)
            assert self.new.args['--boolean'] is not self.arg

        def modifications_to_copied_arguments_do_not_touch_originals(self):
            new_arg = self.new.args['--boolean']
            new_arg.value = True
            assert new_arg.value
            assert not self.arg.value

    class help_for:
        def setup(self):
            # Normal, non-task/collection related Context
            self.vanilla = Context(args=(
                Argument('foo'),
                Argument('bar', help="bar the baz")
            ))
            # Task/Collection generated Context
            # (will expose flags n such)
            @task(help={'otherarg': 'other help'})
            def mytask(myarg, otherarg):
                pass
            col = Collection(mytask)
            self.tasked = col.to_contexts()[0]

        @raises(ValueError)
        def raises_ValueError_for_non_flag_values(self):
            self.vanilla.help_for('foo')

        def vanilla_no_helpstr(self):
            eq_(
                self.vanilla.help_for('--foo'),
                "--foo=STRING"
            )

        def vanilla_with_helpstr(self):
            eq_(
                self.vanilla.help_for('--bar'),
                "--bar=STRING        bar the baz"
            )

        def task_driven_with_helpstr(self):
            eq_(
                self.tasked.help_for('--otherarg'),
                "-o STRING, --otherarg=STRING        other help"
            )

        # Yes, the next 3 tests are identical in form, but technically they
        # test different behaviors. HERPIN' AN' DERPIN'
        def task_driven_no_helpstr(self):
            eq_(
                self.tasked.help_for('--myarg'),
                "-m STRING, --myarg=STRING"
            )

        def short_form_before_long_form(self):
            eq_(
                self.tasked.help_for('--myarg'),
                "-m STRING, --myarg=STRING"
            )

        def equals_sign_for_long_form_only(self):
            eq_(
                self.tasked.help_for('--myarg'),
                "-m STRING, --myarg=STRING"
            )

        def kind_to_placeholder_map(self):
            # str=STRING, int=INT, etc etc
            skip()


    class help_lines:
        def setup(self):
            @task(help={'otherarg': 'other help'})
            def mytask(myarg, otherarg):
                pass
            self.c = Collection(mytask).to_contexts()[0]

        def returns_list_of_help_output_strings(self):
            # Walks own list of flags/args, ensures resulting map to help_for()
            # TODO: consider redoing help_for to be more flexible on input --
            # arg value or flag; or even Argument objects. ?
            eq_(
                self.c.help_lines(),
                [self.c.help_for('--myarg'), self.c.help_for('--otherarg')]
            )

        def _from_args(self, *name_tuples):
            return Context(args=map(lambda x: Argument(names=x), name_tuples))

        def sorts_alphabetically_by_shortflag_first(self):
            # Where shortflags exist, they take precedence
            ctx = self._from_args(('zarg', 'a'), ('arg', 'z') )
            eq_(
                ctx.help_lines(),
                [ctx.help_for('--zarg'), ctx.help_for('--arg')]
            )

        def sorts_alphabetically_by_longflag_when_no_shortflag(self):
            # Where no shortflag, sorts by longflag
            skip()

        def sorts_heterogenous_help_output_with_longflag_only_options_first(self):
            # When both types of options exist, long flag only options come
            # first.
            # E.g.:
            #   --alpha
            #   --beta
            #   -a, --aaaagh
            #   -b, --bah
            #   -c
            skip()
