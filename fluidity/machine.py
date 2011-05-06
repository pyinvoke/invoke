_event_gatherer = []

def event(name, from_, to):
    _event_gatherer.append([name, from_, to])

class MetaStateMachine(type):

    def __new__(cls, name, bases, dictionary):
        global _event_gatherer
        Machine = super(MetaStateMachine, cls).__new__(cls, name, bases, dictionary)
        for i in _event_gatherer:
            Machine.event(*i)
        _event_gatherer = []
        return Machine


class StateMachine(object):

    __metaclass__ = MetaStateMachine

    def __init__(self):
        self._validate()
        self.current_state = self.initial_state

    def _validate(self):
        if not getattr(self, 'states', None) or len(self.states) < 2:
            raise InvalidConfiguration('There must be at least two states')
        if not getattr(self, 'initial_state', None):
            raise InvalidConfiguration('There must exist an initial state')

    @classmethod
    def event(cls, name, from_, to):
        def generated_event(self):
            pass
        generated_event.__doc__ = 'event %s' % name
        generated_event.__name__ = name
        setattr(cls, generated_event.__name__, generated_event)


class InvalidConfiguration(Exception):
    pass

