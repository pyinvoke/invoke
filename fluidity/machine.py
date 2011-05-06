class StateMachine(object):
    def __init__(self):
        if not getattr(self, 'states', None) or len(self.states) < 2:
            raise InvalidConfiguration('There must be at least two states')
        if not getattr(self, 'initial_state', None):
            raise InvalidConfiguration('There must exist an initial state')
        self.current_state = self.initial_state


class InvalidConfiguration(Exception):
    pass

