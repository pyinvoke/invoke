# metaclass implementation idea from
# http://blog.ianbicking.org/more-on-python-metaprogramming-comment-14.html
_transition_gatherer = []

def transition(event, from_, to, action=None, guard=None):
    _transition_gatherer.append([event, from_, to, action, guard])

_state_gatherer = []

def state(name, enter=None, exit=None):
    _state_gatherer.append([name, enter, exit])

class MetaStateMachine(type):

    def __new__(cls, name, bases, dictionary):
        global _transition_gatherer, _state_gatherer
        Machine = super(MetaStateMachine, cls).__new__(cls, name, bases, dictionary)
        Machine._class_transitions = {}
        Machine._class_states = {}
        for i in _transition_gatherer:
            Machine._add_class_transition(*i)
        for s in _state_gatherer:
            Machine._add_class_state(*s)
        _transition_gatherer = []
        _state_gatherer = []
        return Machine


class StateMachine(object):

    __metaclass__ = MetaStateMachine

    def __init__(self):
        self.__class__._validate_machine_definitions()
        if callable(self.initial_state):
            self.initial_state = self.initial_state()
        self.current_state = self.initial_state
        self._handle_state_action(self.initial_state, 'enter')

    @classmethod
    def _validate_machine_definitions(cls):
        if not getattr(cls, '_class_states', None) or len(cls._class_states) < 2:
            raise InvalidConfiguration('There must be at least two states')
        if not getattr(cls, 'initial_state', None):
            raise InvalidConfiguration('There must exist an initial state')

    @classmethod
    def _add_class_state(cls, name, enter, exit):
        cls._class_states[name] = _State(name, enter, exit)

    @classmethod
    def states(cls):
        return cls._class_states

    @classmethod
    def _add_class_transition(cls, event, from_, to, action, guard):
        cls._class_transitions[event] = _Transition(event, from_, to, action, guard)
        this_event = cls._generate_event(event)
        setattr(cls, this_event.__name__, this_event)

    @classmethod
    def _generate_event(cls, name):
        def generated_event(self):
            this_transition = cls._class_transitions[generated_event.__name__]
            from_ = this_transition.from_
            if type(from_) == str:
                from_ = [from_]
            if self.current_state not in from_:
                raise InvalidTransition("Cannot change from %s to %s" % (
                    self.current_state, this_transition.to))
            if not self._check_guard(this_transition.guard):
                raise GuardNotSatisfied("Guard is not satisfied for this transition")
            self._run_transition(this_transition)
        generated_event.__doc__ = 'event %s' % name
        generated_event.__name__ = name
        return generated_event

    def _run_transition(self, transition):
      self._handle_state_action(self.current_state, 'exit')
      self.current_state = transition.to
      self._handle_state_action(transition.to, 'enter')
      self._handle_action(transition.action)

    def _handle_state_action(self, state, kind):
        action = getattr(self._class_states[state], kind)
        self._run_action_or_list(action)

    def _handle_action(self, action):
        self._run_action_or_list(action)

    def _run_action_or_list(self, action_param):
        if not action_param:
            return
        action_items = type(action_param) == list and action_param or [action_param]
        for action_item in action_items:
            if callable(action_item):
                action_item(self)
            else:
                getattr(self, action_item)()

    def _check_guard(self, guard_param):
        if guard_param is None:
            return True
        guard_items = type(guard_param) == list and guard_param or [guard_param]
        result = True
        for guard_item in guard_items:
            if callable(guard_item):
                result = result and guard_item(self)
            else:
                guard = getattr(self, guard_item)
                if callable(guard):
                    guard = guard()
                result = result and guard
        return result


class _Transition(object):

    def __init__(self, event, from_, to, action, guard):
        self.event = event
        self.from_ = from_
        self.to = to
        self.action = action
        self.guard = guard


class _State(object):

    def __init__(self, name, enter, exit):
        self.name = name
        self.enter = enter
        self.exit = exit


class InvalidConfiguration(Exception):
    pass


class InvalidTransition(Exception):
    pass


class GuardNotSatisfied(Exception):
    pass

