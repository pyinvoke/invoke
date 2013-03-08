from operator import add
import types

from .vendor import six
from .vendor.lexicon import Lexicon

from .parser import Context, Argument
from .tasks import Task


class Collection(object):
    """
    A collection of executable tasks.
    """
    def __init__(self, *args, **kwargs):
        """
        Create a new task collection/namespace.

        May call with no arguments and use e.g. `.add_task`/`.add_collection` to insert objects, e.g.::

            c = Collection()
            c.add_task(some_task)

        If an initial string argument is given, it is used as the default name
        for this collection, should it be inserted into another collection as a
        sub-namespace::

            docs = Collection('docs')
            docs.add_task(doc_task)
            ns = Collection()
            ns.add_task(top_level_task)
            ns.add_collection(docs)
            # Valid identifiers are now 'top_level_task' and 'docs.doc_task'
            # (assuming the task objects were actually named the same as the
            # variables we're using :))

        Otherwise, all ``*args`` are expected to be `.Task` or `.Collection`
        instances which will be passed to `.add_task`/`.add_collection` as
        appropriate. Module objects are also valid (as they are for
        `.add_collection`). For example, the below snippet results in the same
        two task identifiers as the one above::

            ns = Collection(top_level_task, Collection('docs', doc_task))

        If any ``**kwargs`` are given, the keywords are used as the initial
        name arguments for the respective values::

            ns = Collection(
                top_level_task=some_other_task,
                docs=Collection(doc_task)
            )

        That's exactly equivalent to::

            docs = Collection(doc_task)
            ns = Collection()
            ns.add_task(some_other_task, 'top_level_task')
            ns.add_collection(docs, 'docs')
        """
        # Initialize
        self.tasks = Lexicon()
        self.collections = Lexicon()
        self.default = None
        self.name = None
        # Name if applicable
        args = list(args)
        if args and isinstance(args[0], six.string_types):
            self.name = args.pop(0)
        # Dispatch args/kwargs
        for arg in args:
            self._add_object(arg)
        # Dispatch kwargs
        for name, obj in six.iteritems(kwargs):
            self._add_object(obj, name)

    def _add_object(self, obj, name=None):
        if isinstance(obj, Task):
            method = self.add_task
        elif isinstance(obj, (Collection, types.ModuleType)):
            method = self.add_collection
        else:
            raise TypeError("No idea how to insert %r!" % type(obj))
        return method(obj, name=name)

    @classmethod
    def from_module(self, module):
        """
        Return a new `.Collection` created from ``module``.

        Inspects ``module`` for any `.Task` instances and adds them to a new
        `.Collection`, returning it. If any explicit namespace collections
        exist (named ``ns`` or ``namespace``) they are preferentially loaded
        instead.

        When the implicit/default collection is generated, it will be named
        after the module's ``__name__`` attribute, or its last dotted section
        if it's a submodule. (I.e. it should usually map to the actual ``.py``
        filename.)

        Explicitly given collections will only be given that module-derived
        name if they don't already have a valid ``.name`` attribute.
        """
        module_name = module.__name__.split('.')[-1]
        # See if the module provides a default NS to use in lieu of creating
        # our own collection.
        for candidate in ('ns', 'namespace'):
            obj = getattr(module, candidate, None)
            if obj and isinstance(obj, Collection):
                if not obj.name:
                    obj.name = module_name
                return obj
        # Failing that, make our own collection from the module's tasks.
        tasks = filter(
            lambda x: isinstance(x[1], Task),
            vars(module).items()
        )
        collection = Collection(module_name)
        for name, task in tasks:
            collection.add_task(name=name, task=task)
        return collection

    def add_task(self, task, name=None):
        """
        Adds ``Task`` ``task`` to this collection.

        If ``name`` is not explicitly given (recommended) the ``.__name__`` of
        the ``Task``'s wrapped callable will be used instead. (If the wrapped
        callable is not a function, you *must* give ``name``.)
        """
        if name is None:
            if hasattr(task.body, '__name__'):
                name = task.body.__name__
            else:
                raise ValueError("'name' may only be empty if 'task' wraps an object exposing .__name__")
        if name in self.collections:
            raise ValueError("Name conflict: this collection has a sub-collection named %r already" % name)
        self.tasks[name] = task
        for alias in task.aliases:
            self.tasks.alias(alias, to=name)
        if task.is_default:
            if self.default:
                msg = "'%s' cannot be the default because '%s' already is!"
                raise ValueError(msg % (name, self.default))
            self.default = name

    def add_collection(self, coll, name=None):
        # Handle module-as-collection
        if isinstance(coll, types.ModuleType):
            coll = Collection.from_module(coll)
        # Ensure we have a name, or die trying
        name = name or coll.name
        if not name:
            raise ValueError("Non-root collections must have a name!")
        # Test for conflict
        if name in self.tasks:
            raise ValueError("Name conflict: this collection has a task named %r already" % name)
        # Insert
        self.collections[name] = coll

    def __getitem__(self, name=None):
        """
        Returns task named ``name``. Honors aliases and subcollections.

        If this collection has a default task, it is returned when ``name`` is
        empty or ``None``. If empty input is given and no task has been
        selected as the default, ValueError will be raised.

        Tasks within subcollections should be given in dotted form, e.g.
        'foo.bar'. Subcollection default tasks will be returned on the
        subcollection's name.
        """
        # Default task for this collection itself
        if not name:
            if self.default:
                return self[self.default]
            else:
                raise ValueError("This collection has no default task.")
        # Non-default tasks within subcollections
        if '.' in name:
            parts = name.split('.')
            coll = parts.pop(0)
            rest = '.'.join(parts)
            return self.collections[coll][rest]
        # Default task for subcollections (via empty-name lookup)
        if name in self.collections:
            return self.collections[name]['']
        # Regular task lookup
        return self.tasks[name]

    def __contains__(self, name):
        try:
            task = self[name]
            return True
        except KeyError:
            return False

    def to_contexts(self):
        """
        Returns all contained tasks and subtasks as a list of parser contexts.
        """
        result = []
        for primary, aliases in six.iteritems(self.task_names):
            task = self[primary]
            result.append(Context(
                name=primary, aliases=aliases, args=task.get_arguments()
            ))
        return result

    def subtask_name(self, collection_name, task_name):
        return "%s.%s" % (collection_name, task_name)

    @property
    def task_names(self):
        """
        Return all task identifiers for this collection as a dict.

        Specifically, a dict with the primary/"real" task names as the key, and
        any aliases as a list value.
        """
        ret = {}
        # Our own tasks get no prefix, just go in as-is: {name: [aliases]}
        for name, task in six.iteritems(self.tasks):
            ret[name] = task.aliases
        # Subcollection tasks get both name + aliases prefixed
        for coll_name, coll in six.iteritems(self.collections):
            for task_name, aliases in six.iteritems(coll.task_names):
                # Cast to list to handle Py3 map() 'map' return value,
                # so we can add to it down below if necessary.
                aliases = list(map(
                    lambda x: self.subtask_name(coll_name, x),
                    aliases
                ))
                # Tack on collection name to alias list if this task is the
                # collection's default.
                if coll.default and coll.default == task_name:
                    aliases += (coll_name,)
                ret[self.subtask_name(coll_name, task_name)] = aliases
        return ret
