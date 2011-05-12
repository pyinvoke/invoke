import unittest
from should_dsl import should
from fluidity import StateMachine, state, transition


class CrazyGuy(StateMachine):
    state('looking', exit='no_lookin_anymore')
    state('falling', enter='will_fall_right_now')
    initial_state = 'looking'
    transition(from_='looking', event='jump', to='falling',
               action='become_at_risk', guard='always_can_jump')

    def __init__(self):
        StateMachine.__init__(self)
        self.at_risk = False
        self.callbacks = []

    def become_at_risk(self):
        self.at_risk = True
        self.callbacks.append('action')

    def no_lookin_anymore(self):
        self.callbacks.append('old exit')

    def will_fall_right_now(self):
        self.callbacks.append('new enter')

    def always_can_jump(self):
        self.callbacks.append('guard')
        return True


class CallbackOrder(unittest.TestCase):

    def setUp(self):
        guy = CrazyGuy()
        guy.jump()
        self.callbacks = guy.callbacks

    def it_runs_guard_first(self):
        '''(1) guard'''
        self.callbacks[0] |should| equal_to('guard')

    def it_and_then_old_state_exit(self):
        '''(2) old state exit action'''
        self.callbacks[1] |should| equal_to('old exit')

    def it_and_then_new_state_exit(self):
        '''(3) new state enter action'''
        self.callbacks[2] |should| equal_to('new enter')

    def it_and_then_transaction_action(self):
        '''(4) transaction action'''
        self.callbacks[3] |should| equal_to('action')

