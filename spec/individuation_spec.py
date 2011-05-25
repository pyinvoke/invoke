import unittest
from should_dsl import should
from fluidity import StateMachine, state, transition


class Door(StateMachine):
    state('closed')
    state('open')
    initial_state = 'closed'
    transition(from_='closed', event='open', to='open')


class IndividuationSpec(unittest.TestCase):
    '''Fluidity object (individuation)'''

    def it_responds_to_an_event(self):
        door = Door()
        door.add_state('broken')
        door.add_transition(from_='closed', event='crack', to='broken')
        door |should| respond_to('crack')

