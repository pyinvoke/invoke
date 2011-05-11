import unittest
from should_dsl import should, should_not
from fluidity import StateMachine, state, transition
from fluidity import InvalidTransition


class MyMachine(StateMachine):

     initial_state = 'created'

     state('created')
     state('waiting')
     state('processed')
     state('canceled')

     transition(from_='created', event='queue', to='waiting')
     transition(from_='waiting', event='process', to='processed')
     transition(from_=['waiting', 'created'], event='cancel', to='canceled')


class FluidityEvent(unittest.TestCase):

    def its_declaration_creates_a_method_with_its_name(self):
        machine = MyMachine()
        machine |should| respond_to('queue')
        machine |should| respond_to('process')

    def it_changes_machine_state(self):
        machine = MyMachine()
        machine.current_state |should| equal_to('created')
        machine.queue()
        machine.current_state |should| equal_to('waiting')
        machine.process()
        machine.current_state |should| equal_to('processed')

    def it_ensures_event_order(self):
        machine = MyMachine()
        machine.process |should| throw(InvalidTransition)
        machine.queue()
        machine.queue |should| throw(InvalidTransition)
        machine.process |should_not| throw(Exception)

    def it_accepts_multiple_origin_states(self):
        machine = MyMachine()
        machine.cancel |should_not| throw(Exception)

        machine = MyMachine()
        machine.queue()
        machine.cancel |should_not| throw(Exception)

        machine = MyMachine()
        machine.queue()
        machine.process()
        machine.cancel |should| throw(Exception)

