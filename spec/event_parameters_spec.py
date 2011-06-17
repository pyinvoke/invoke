import unittest
from should_dsl import should
from fluidity import StateMachine, state, transition


class Door(StateMachine):
    state('closed')
    state('open')
    initial_state = 'closed'
    transition(from_='closed', event='open', to='open', action='open_action')
    transition(from_='open', event='close', to='closed', action='close_action')

    def open_action(self, when, where):
        self.when = when
        self.where = where

    def close_action(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class EventParameters(unittest.TestCase):

    def test_it_pass_parameters_received_by_event_to_action(self):
        door = Door()
        door.open('now!', 'there!')
        door |should| respond_to('when')
        door.when |should| equal_to('now!')
        door |should| respond_to('where')
        door.where |should| equal_to('there!')

    def test_it_pass_args_and_kwargs_to_action(self):
        door = Door()
        door.open('anytime', 'anywhere')
        door.close('1', 2, object, test=9, it=8, works=7)
        door |should| respond_to('args')
        door.args |should| equal_to(('1', 2, object))
        door |should| respond_to('kwargs')
        door.kwargs |should| equal_to({'test': 9, 'it': 8, 'works': 7})


if __name__ == '__main__':
    unittest.main()

