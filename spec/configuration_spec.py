import unittest
from should_dsl import should
from fluidity import StateMachine, state, InvalidConfiguration


class FluidityConfigurationValidation(unittest.TestCase):

    def test_it_requires_at_least_two_states(self):
        class MyMachine(StateMachine):
            pass
        MyMachine |should| throw(InvalidConfiguration,
            message="There must be at least two states")
        class OtherMachine(StateMachine):
            state('open')
        OtherMachine |should| throw(InvalidConfiguration,
            message="There must be at least two states")

    def test_it_requires_an_initial_state(self):
        class MyMachine(StateMachine):
            state('open')
            state('closed')
        MyMachine |should| throw(InvalidConfiguration,
            message="There must exist an initial state")
        class AnotherMachine(StateMachine):
            state('open')
            state('closed')
            initial_state = None
        AnotherMachine |should| throw(InvalidConfiguration,
            message="There must exist an initial state")


if __name__ == '__main__':
    unittest.main()

