import unittest
import new
from should_dsl import should, should_not
from fluidity.machine import StateMachine, event, state
from fluidity.machine import InvalidTransition, InvalidConfiguration


class FluidityStateMachine(unittest.TestCase):

    def it_defines_states(self):
        class MyMachine(StateMachine):
            state('unread')
            state('read')
            state('closed')
            initial_state = 'read'
        machine = MyMachine()
        machine |should| have(3).states
        machine.states() |should| include_all_of(['unread', 'read', 'closed'])

    def it_has_an_initial_state(self):
        class MyMachine(StateMachine):
            initial_state = 'closed'
            state('open')
            state('closed')
        machine = MyMachine()
        machine.initial_state |should| equal_to('closed')
        machine.current_state |should| equal_to('closed')

    def it_defines_states_using_method_calls(self):
        class MyMachine(StateMachine):
            state('unread')
            state('read')
            state('closed')
            initial_state = 'unread'
            event('read', from_='unread', to='read')
            event('close', from_='read', to='closed')
        machine = MyMachine()
        machine |should| have(3).states
        machine.states() |should| include_all_of(['unread', 'read', 'closed'])

        class OtherMachine(StateMachine):
            state('idle')
            state('working')
            initial_state = 'idle'
            event('work', from_='idle', to='working')
        machine = OtherMachine()
        machine |should| have(2).states
        machine.states() |should| include_all_of(['idle', 'working'])


class FluidityConfigurationValidation(unittest.TestCase):

    def it_requires_at_least_two_states(self):
        class MyMachine(StateMachine):
            pass
        MyMachine |should| throw(InvalidConfiguration,
            message="There must be at least two states")
        class OtherMachine(StateMachine):
            state('open')
        OtherMachine |should| throw(InvalidConfiguration,
            message="There must be at least two states")

    def it_requires_an_initial_state(self):
        class MyMachine(StateMachine):
            state('open')
            state('closed')
        MyMachine |should| throw(InvalidConfiguration,
            message="There must exist an initial state")
        class AnotherMachine(StateMachine):
            state('open')
            state('closed')
            initial_state = None
        AnotherMachine |should| throw(InvalidConfiguration,
            message="There must exist an initial state")


class MyMachine(StateMachine):
     initial_state = 'created'
     state('created')
     state('waiting')
     state('processed')
     state('canceled')
     event('queue', from_='created', to='waiting')
     event('process', from_='waiting', to='processed')
     event('cancel', from_=['waiting', 'created'], to='canceled')


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


class ActionMachine(StateMachine):
      state('created', exit='post_create')
      state('waiting', enter='pre_wait')
      initial_state = 'created'
      event('queue', from_='created', to='waiting')
      def __init__(self):
          super(ActionMachine, self).__init__()
          self.is_enter_aware = False
          self.is_exit_aware = False
          self.count = 0
      def pre_wait(self):
          self.is_enter_aware = True
          if getattr(self, 'pre_wait_expectation', None):
              self.pre_wait_expectation()
      def post_create(self):
          self.is_exit_aware = True
          if getattr(self, 'post_create_expectation', None):
              self.post_create_expectation()


class FluidityAction(unittest.TestCase):

      def it_runs_enter_action_before_machine_enters_a_given_state(self):
          machine = ActionMachine()
          machine |should_not| be_enter_aware
          machine.queue()
          machine |should| be_enter_aware

      def it_runs_exit_action_after_machine_exits_a_given_state(self):
          machine = ActionMachine()
          machine |should_not| be_exit_aware
          machine.queue()
          machine |should| be_enter_aware

      def it_runs_exit_action_before_enter_action(self):
          '''it runs old state's exit action before new state's enter action'''
          machine = ActionMachine()
          def post_create_expectation(_self):
              _self.count +=1
              _self.count |should| be(1)
          def pre_wait_expectation(_self):
              _self.count += 1
              _self.count |should| be(2)
          machine.post_create_expectation = new.instancemethod(
              post_create_expectation, machine, ActionMachine)
          machine.pre_wait_expectation = new.instancemethod(
              pre_wait_expectation, machine, ActionMachine)
          machine.queue()

