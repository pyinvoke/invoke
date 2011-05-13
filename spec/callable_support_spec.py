import unittest
from should_dsl import should
from fluidity import StateMachine, state, transition


class JumperGuy(StateMachine):
    state('looking', enter=lambda jumper: jumper.footsteps.append('enter looking'),
                     exit=lambda jumper: jumper.footsteps.append('exit looking'))
    state('falling', enter=lambda jumper: jumper.footsteps.append('enter falling'))
    initial_state = 'looking'

    transition(from_='looking', event='jump', to='falling',
               action=lambda jumper: jumper.footsteps.append('action jump'),
               guard=lambda jumper: jumper.footsteps.append('guard jump') is None)

    def __init__(self):
        self.footsteps = []
        StateMachine.__init__(self)


class CallableSupport(unittest.TestCase):

    def test_every_callback_can_be_a_callable(self):
        '''every callback can be a callable'''
        guy = JumperGuy()
        guy.jump()
        guy |should| have(5).footsteps
        guy.footsteps |should| include_all_of([
            'enter looking', 'exit looking', 'enter falling',
            'action jump', 'guard jump'])

