import types

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
        Machine._class_transitions = []
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

    def __new__(cls, *args, **kwargs):
        obj = super(StateMachine, cls).__new__(cls)
        obj._states = {}
        obj._transitions = []
        return obj

    @classmethod
    def _validate_machine_definitions(cls):
        if not getattr(cls, '_class_states', None) or len(cls._class_states) < 2:
            raise InvalidConfiguration('There must be at least two states')
        if not getattr(cls, 'initial_state', None):
            raise InvalidConfiguration('There must exist an initial state')

    @classmethod
    def _add_class_state(cls, name, enter, exit):
        cls._class_states[name] = _State(name, enter, exit)

    def add_state(self, name, enter=None, exit=None):
        self._states[name] = _State(name, enter, exit)

    def states(self):
        return self.__class__._class_states.keys() + self._states.keys()

    @classmethod
    def _add_class_transition(cls, event, from_, to, action, guard):
        cls._class_transitions.append(_Transition(event, from_, to, action, guard))
        this_event = cls._generate_event(event)
        setattr(cls, this_event.__name__, this_event)

    def add_transition(self, event, from_, to, action=None, guard=None):
        self._transitions.append(_Transition(event, from_, to, action, guard))
        this_event = self.__class__._generate_event(event)
        setattr(self, this_event.__name__,
            types.MethodType(this_event, self, self.__class__))

    @classmethod
    def _generate_event(cls, name):
        def generated_event(self, *args, **kwargs):
            these_transitions = self._transitions_by_name(generated_event.__name__)
            these_transitions = self._ensure_from_validity(these_transitions)
            this_transition = self._check_guards(these_transitions)
            self._run_transition(this_transition, *args, **kwargs)
        generated_event.__doc__ = 'event %s' % name
        generated_event.__name__ = name
        return generated_event

    def _transitions_by_name(self, name):
        return filter(lambda transition: transition.event == name,
            self.__class__._class_transitions + self._transitions)

    def _ensure_from_validity(self, transitions):
        valid_transitions = []
        for transition in transitions:
            from_ = _listize(transition.from_)
            if self.current_state in from_:
                valid_transitions.append(transition)
        if len(valid_transitions) == 0:
            raise InvalidTransition("Cannot change from %s to %s" % (
                self.current_state, transition.to))
        return valid_transitions

    def _check_guards(self, transitions):
        for transition in transitions:
            if self._check_guard(transition.guard):
                return transition
        raise GuardNotSatisfied("Guard is not satisfied for this transition")

    def _run_transition(self, transition, *args, **kwargs):
        self._handle_state_action(self.current_state, 'exit')
        self.current_state = transition.to
        self._handle_state_action(transition.to, 'enter')
        self._handle_action(transition.action, *args, **kwargs)

    def _handle_state_action(self, state, kind):
        try:
            action = getattr(self._class_states[state], kind)
        except KeyError:
            action = getattr(self._states[state], kind)
        self._run_action_or_list(action)

    def _handle_action(self, action, *args, **kwargs):
        self._run_action_or_list(action, *args, **kwargs)

    def _run_action_or_list(self, action_param, *args, **kwargs):
        if not action_param:
            return
        action_items = _listize(action_param)
        for action_item in action_items:
            self._run_action(action_item, *args, **kwargs)

    def _run_action(self, action, *args, **kwargs):
        if callable(action):
            self._try_to_run_with_args(action, self, *args, **kwargs)
        else:
            self._try_to_run_with_args(getattr(self, action), *args, **kwargs)

    def _try_to_run_with_args(self, action, *args, **kwargs):
        try:
            action(*args, **kwargs)
        except TypeError:
            if len(args) > 0 and args[0] == self:
                action(self)
            else:
                action()

    def _check_guard(self, guard_param):
        if guard_param is None:
            return True
        guard_items = _listize(guard_param)
        result = True
        for guard_item in guard_items:
            result = result and self._evaluate_guard(guard_item)
        return result

    def _evaluate_guard(self, guard):
        if callable(guard):
            return guard(self)
        else:
            guard = getattr(self, guard)
            if callable(guard):
                guard = guard()
            return guard


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


def _listize(value):
    return type(value) in [list, tuple] and value or [value]

