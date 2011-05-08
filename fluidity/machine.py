# metaclass implementation idea from
# http://blog.ianbicking.org/more-on-python-metaprogramming-comment-14.html
_event_gatherer = []

def event(name, from_, to):
    _event_gatherer.append([name, from_, to])

_state_gatherer = []

def state(name):
    _state_gatherer.append(name)

class MetaStateMachine(type):

    def __new__(cls, name, bases, dictionary):
        global _event_gatherer, _state_gatherer
        Machine = super(MetaStateMachine, cls).__new__(cls, name, bases, dictionary)
        Machine._events = {}
        for i in _event_gatherer:
            Machine.event(*i)
        for s in _state_gatherer:
            Machine.state(s)
        _event_gatherer = []
        _state_gatherer = []
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
    def state(cls, name):
        if not getattr(cls, 'states', None):
            cls.states = []
        cls.states.append(name)

    @classmethod
    def event(cls, name, from_, to):
        cls._events[name] = _Event(name, from_, to)
        this_event = cls._generate_event(name)
        setattr(cls, this_event.__name__, this_event)

    @classmethod
    def _generate_event(cls, name):
        def generated_event(self):
            this_event = cls._events[generated_event.__name__]
            from_ = this_event.from_
            if type(from_) == str:
                from_ = [from_]
            if self.current_state not in from_:
                raise InvalidTransition("Cannot change from %s to %s" % (
                    self.current_state, this_event.to))
            self.current_state = cls._events[generated_event.__name__].to
        generated_event.__doc__ = 'event %s' % name
        generated_event.__name__ = name
        return generated_event


class _Event(object):

    def __init__(self, name, from_, to):
        self.name = name
        self.from_ = from_
        self.to = to


class InvalidConfiguration(Exception):
    pass


class InvalidTransition(Exception):
    pass

