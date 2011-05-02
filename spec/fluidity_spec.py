import unittest
from should_dsl import should, should_not, matcher
from fluidity.machine import StateMachine


class FluiditySpec(unittest.TestCase):

    def it_defines_states(self):
        class MyMachine(StateMachine):
            states = ['unread', 'read', 'closed']
        machine = MyMachine()
        machine |should| have(3).states
        machine.states |should| include_all_of(['unread', 'read', 'closed'])

    def it_has_an_initial_state(self):
        class MyMachine(StateMachine):
            initial_state = 'closed'
        machine = MyMachine()
        machine.initial_state |should| equal_to('closed')

