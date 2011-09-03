Fluidity
========

State machine implementation for Python objects.


How to use
----------

A very simple example taken from specs::

    from fluidity import StateMachine, state, transition

    class SimpleMachine(StateMachine):

         initial_state = 'created'

         state('created')
         state('waiting')
         state('processed')
         state('canceled')

         transition(from_='created', event='queue', to='waiting')
         transition(from_='waiting', event='process', to='processed')
         transition(from_=['waiting', 'created'], event='cancel', to='canceled')


"A slightly more complex example"
---------------------------------

For demonstrating more advanced capabilities, a "slightly more complex example" from `AASM <https://github.com/rubyist/aasm>`_, the Ruby's most popular state machine implementation, is reproduced below, using Fluidity::


    from fluidity import StateMachine, state, transition

    class Relationship(StateMachine):
        initial_state = lambda relationship: relationship.strictly_for_fun() and 'intimate' or 'dating'
        state('dating', enter='make_happy', exit='make_depressed')
        state('intimate', enter='make_very_happy', exit='never_speak_again')
        state('married', enter='give_up_intimacy', exit='buy_exotic_car_and_buy_a_combover')

        transition(from_='dating', event='get_intimate', to='intimate', guard='drunk')
        transition(from_=['dating', 'intimate'], event='get_married', to='married', guard='willing_to_give_up_manhood')

        def strictly_for_fun(self): pass
        def drunk(self): pass
        def willing_to_give_up_manhood(self): return True
        def make_happy(self): pass
        def make_depressed(self): pass
        def make_very_happy(self): pass
        def never_speak_again(self): pass
        def give_up_intimacy(self): pass
        def buy_exotic_car_and_buy_a_combover(self): pass


States
------

A Fluidity state machine must have one initial state and at least two states.

A state may have enter and exit callbacks, for running some code on state enter
and exit, respectively. These params can be method names (as strings),
callables, or lists of method names or callables.


Transitions
-----------

Transitions lead the machine from a state to another. Transitions must have
*from\_*, *to*, and *action* parameters. *from\_* is one or more (as list) states
from which the transition can be started. *to* is the state to which the
transition will lead the machine. *event* is the method that have to be called
to launch the transition. This method is automatically created by the Fluidity
engine.

A transition can have optional *action* and *guard* parameters. *action* is a
method (or callable) that will be called when transition is launched. If
parameters are passed to the event method, they are passed to the *action*
method, if it accepts these parameters. *guard* is a method (or callable) that
is called to allow or deny the transition, depending on the result of its
execution. Both "action" and *guard* can be lists.

The same event can be in multiple transitions, going to different states, having
their respective guards as selectors. For the transitions having the same event,
only one guard should return a true value at a time.


Individuation
-------------

States and transitions are defined in a class-wide mode. However, one can define
states and transitions for individual objects. For example, having "door" as a
state machine::

    door.add_state('broken')
    door.add_transition(from_='closed', event='crack', to='broken')


These additions only affect the target object.


How to install
--------------

Just run::

    pip install fluidity-sm


**Note**: the Pypi package is called *fluidity-sm*, not *fluidity*.


How to run tests
----------------

Just run::

    make test

for install all test dependencies (`Should-DSL <http://www.should-dsl.info>`_
and `Specloud <https://github.com/hugobr/specloud>`_, at the moment) and
run the tests. Fluidity itself has no dependencies.

