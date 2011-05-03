class StateMachine(object):
    def __init__(self):
        if not getattr(self, 'states', None) or len(self.states) < 2:
            raise InvalidConfiguration('There must be at least two states')


class InvalidConfiguration(Exception):
    pass

