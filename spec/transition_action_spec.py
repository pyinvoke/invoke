import unittest
from should_dsl import should, should_not
from fluidity import StateMachine, state, transition


class CrazyGuy(StateMachine):
    state('looking')
    state('falling')
    initial_state = 'looking'
    transition(from_='looking', event='jump', to='falling', action='become_at_risk')

    def __init__(self):
        StateMachine.__init__(self)
        self.at_risk = False

    def become_at_risk(self):
        self.at_risk = True


class FluidityTransitionAction(unittest.TestCase):

      def it_runs_when_transition_occurs(self):
          guy = CrazyGuy()
          guy |should_not| be_at_risk
          guy.jump()
          guy |should| be_at_risk

