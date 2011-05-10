import unittest
from should_dsl import should
from fluidity.machine import StateMachine, transition, state


class FluidityState(unittest.TestCase):

    def it_defines_states(self):
        class MyMachine(StateMachine):
            state('unread')
            state('read')
            state('closed')
            initial_state = 'read'
        machine = MyMachine()
        machine |should| have(3).states
        machine.states() |should| include_all_of(['unread', 'read', 'closed'])

    def it_has_an_initial_state(self):
        class MyMachine(StateMachine):
            initial_state = 'closed'
            state('open')
            state('closed')
        machine = MyMachine()
        machine.initial_state |should| equal_to('closed')
        machine.current_state |should| equal_to('closed')

    def it_defines_states_using_method_calls(self):
        class MyMachine(StateMachine):
            state('unread')
            state('read')
            state('closed')
            initial_state = 'unread'
            transition(from_='unread', event='read', to='read')
            transition(from_='read', event='close', to='closed')
        machine = MyMachine()
        machine |should| have(3).states
        machine.states() |should| include_all_of(['unread', 'read', 'closed'])

        class OtherMachine(StateMachine):
            state('idle')
            state('working')
            initial_state = 'idle'
            transition(from_='idle', event='work', to='working')
        machine = OtherMachine()
        machine |should| have(2).states
        machine.states() |should| include_all_of(['idle', 'working'])

