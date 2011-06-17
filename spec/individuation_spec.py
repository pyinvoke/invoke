import unittest
from should_dsl import should, should_not
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

    def test_it_responds_to_an_event(self):
        self.door |should| respond_to('crack')

    def test_its_event_changes_its_state_when_called(self):
        self.door.crack()
        self.door.current_state |should| equal_to('broken')

    def test_it_informs_all_its_states(self):
        self.door |should| have(3).states
        self.door.states() |should| include_all_of(['open', 'closed', 'broken'])

    def test_its_individuation_does_not_affect_other_objects_from_the_same_class(self):
        another_door = Door()
        another_door |should_not| respond_to('crack')


if __name__ == '__main__':
    unittest.main()

