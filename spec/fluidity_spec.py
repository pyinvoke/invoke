import unittest
from should_dsl import should
from fluidity.machine import StateMachine, InvalidConfiguration


class FluiditySpec(unittest.TestCase):

    def it_defines_states(self):
        class MyMachine(StateMachine):
            states = ['unread', 'read', 'closed']
            initial_state = 'read'
        machine = MyMachine()
        machine |should| have(3).states
        machine.states |should| include_all_of(['unread', 'read', 'closed'])

    def it_has_an_initial_state(self):
        class MyMachine(StateMachine):
            initial_state = 'closed'
            states = ['open', 'closed']
        machine = MyMachine()
        machine.initial_state |should| equal_to('closed')

    def it_requires_at_least_two_states(self):
        class MyMachine(StateMachine):
            pass
        MyMachine |should| throw(InvalidConfiguration,
            message="There must be at least two states")
        class OtherMachine(StateMachine):
            states = ['open']
        OtherMachine |should| throw(InvalidConfiguration,
            message="There must be at least two states")

    def it_requires_an_initial_state(self):
        class MyMachine(StateMachine):
            states = ['open', 'closed']
        MyMachine |should| throw(InvalidConfiguration,
            message="There must exist an initial state")
        class AnotherMachine(StateMachine):
            states = ['open', 'closed']
            initial_state = None
        AnotherMachine |should| throw(InvalidConfiguration,
            message="There must exist an initial state")

