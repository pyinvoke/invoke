import unittest
from should_dsl import should
from fluidity import StateMachine, state, transition
from fluidity import GuardNotSatisfied


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

    def it_should_deny_state_change_if_guard_callable_returns_false(self):
        class Door(StateMachine):
            state('open')
            state('closed')
            initial_state = 'closed'
            transition(from_='closed', event='open', to='open',
                       guard=lambda d: not door.locked)
            def locked(self):
                return self.locked

        door = Door()
        door.locked = True
        door.open |should| throw(GuardNotSatisfied)

