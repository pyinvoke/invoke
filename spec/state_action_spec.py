import unittest
import new
from should_dsl import should, should_not
from fluidity import StateMachine, state, transition


class ActionMachine(StateMachine):

      state('created', enter='about_to_create',
                       exit=['other_post_create', 'post_create'])
      state('waiting', enter=['pre_wait', 'other_pre_wait'])
      initial_state = 'created'
      transition(from_='created', event='queue', to='waiting')

      def __init__(self):
          self.enter_create = False
          super(ActionMachine, self).__init__()
          self.is_enter_aware = False
          self.is_exit_aware = False
          self.pre_wait_aware = False
          self.other_pre_wait_aware = False
          self.post_create_aware = False
          self.other_post_create_aware = False
          self.count = 0

      def pre_wait(self):
          self.is_enter_aware = True
          self.pre_wait_aware = True
          if getattr(self, 'pre_wait_expectation', None):
              self.pre_wait_expectation()

      def post_create(self):
          self.is_exit_aware = True
          self.post_create_aware = True
          if getattr(self, 'post_create_expectation', None):
              self.post_create_expectation()

      def about_to_create(self):
          self.enter_create = True

      def other_pre_wait(self):
          self.other_pre_wait_aware = True

      def other_post_create(self):
          self.other_post_create_aware = True



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

      def it_runs_enter_action_for_initial_state_at_creation(self):
          ActionMachine().enter_create |should| be(True)

      def it_accepts_many_enter_actions(self):
          machine = ActionMachine()
          machine |should_not| be_pre_wait_aware
          machine |should_not| be_other_pre_wait_aware
          machine.queue()
          machine |should| be_pre_wait_aware
          machine |should| be_other_pre_wait_aware

      def it_accepts_exit_actions(self):
          machine = ActionMachine()
          machine |should_not| be_post_create_aware
          machine |should_not| be_other_post_create_aware
          machine.queue()
          machine |should| be_post_create_aware
          machine |should| be_other_post_create_aware

