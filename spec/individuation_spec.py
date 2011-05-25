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

    def setUp(self):
        self.door = Door()
        self.door.add_state('broken')
        self.door.add_transition(from_='closed', event='crack', to='broken')

    def it_responds_to_an_event(self):
        self.door |should| respond_to('crack')

    def its_event_changes_its_state_when_called(self):
        self.door.crack()
        self.door.current_state |should| equal_to('broken')

    def it_informs_all_its_states(self):
        self.door |should| have(3).states
        self.door.states() |should| include_all_of(['open', 'closed', 'broken'])

