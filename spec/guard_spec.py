import unittest
from should_dsl import should, should_not
from fluidity import StateMachine, state, transition
from fluidity import GuardNotSatisfied


class FallingMachine(StateMachine):
    state('looking')
    state('falling')
    initial_state = 'looking'
    transition(from_='looking', event='jump', to='falling', guard='ready_to_fly')

    def __init__(self, ready=True):
        StateMachine.__init__(self)
        self.ready = ready

    def ready_to_fly(self):
        return self.ready


class FluidityGuard(unittest.TestCase):

    def it_allows_transition_if_satisfied(self):
        machine = FallingMachine()
        machine.jump |should_not| throw(Exception)
        machine.current_state |should| equal_to('falling')

    def it_forbids_transition_if_not_satisfied(self):
        machine = FallingMachine(ready=False)
        machine.jump |should| throw(GuardNotSatisfied)

    def it_may_be_an_attribute(self):
        '''it may be an attribute, not only a method'''
        machine = FallingMachine()
        machine.ready_to_fly = False
        machine.jump |should| throw(GuardNotSatisfied)

        machine.ready_to_fly = True
        machine.jump |should_not| throw(Exception)
        machine.current_state |should| equal_to('falling')

