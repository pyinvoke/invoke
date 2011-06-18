import unittest
from should_dsl import should, should_not
from fluidity import StateMachine, state, transition, ForkedTransition


class LoanRequest(StateMachine):
    state('pending')
    state('analyzing')
    state('refused')
    state('accepted')
    initial_state = 'pending'
    transition(from_='pending', event='analyze', to='analyzing', action='input_data')
    transition(from_='analyzing', event='forward_analysis_result',
               guard='was_loan_accepted', to='accepted')
    transition(from_='analyzing', event='forward_analysis_result',
               guard='was_loan_refused', to='refused')

    def input_data(self, accepted=True):
        self.accepted = accepted

    def was_loan_accepted(self):
        return self.accepted or getattr(self, 'truify', False)

    def was_loan_refused(self):
        return not self.accepted or getattr(self, 'truify', False)


class FluidityEventSupportsMultipleTransitions(unittest.TestCase):
    '''Event chooses one of multiple transitions, based in their guards'''

    def test_it_selects_the_transition_having_a_passing_guard(self):
        request = LoanRequest()
        request.analyze()
        request.forward_analysis_result()
        request.current_state |should| equal_to('accepted')

        request = LoanRequest()
        request.analyze(accepted=False)
        request.forward_analysis_result()
        request.current_state |should| equal_to('refused')

    def test_it_raises_error_if_more_than_one_guard_passes(self):
        request = LoanRequest()
        request.analyze()
        request.truify = True
        request.forward_analysis_result |should| throw(
            ForkedTransition, message="More than one transition was allowed for this event")



if __name__ == '__main__':
    unittest.main()

