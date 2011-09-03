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

