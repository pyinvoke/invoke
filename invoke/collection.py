import copy
import types

try:
    from .vendor import six
    from .vendor.lexicon import Lexicon
except ImportError:
    # Use system wide modules
    import six
    from lexicon import Lexicon


from .config import merge_dicts, copy_dict
from .parser import Context as ParserContext
from .tasks import Task


class Collection(object):
    """
    A collection of executable tasks.
    """
    def __init__(self, *args, **kwargs):
        """
        Create a new task collection/namespace.

        `.Collection` offers a set of methods for building a collection of
        tasks from scratch, plus a convenient constructor wrapping said API.

        In either case:

        * the first positional argument may be a string, which (if given) is
          used as the collection's default name when performing namespace
          lookups;
        * a ``loaded_from`` keyword argument may be given, which sets metadata
          indicating the filesystem path the collection was loaded from. This
          is used as a guide when loading per-project :ref:`configuration files
          <config-hierarchy>`.

        **The method approach**

        May initialize with no arguments and use methods (e.g.
        `.add_task`/`.add_collection`) to insert objects::

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

        For details, see the API docs for the rest of the class.

        **The constructor approach**

        All ``*args`` given to `.Collection` (besides the abovementioned
        optional positional 'name' argument and ``loaded_from`` kwarg) are
        expected to be `.Task` or `.Collection` instances which will be passed
        to `.add_task`/`.add_collection` as appropriate. Module objects are
        also valid (as they are for `.add_collection`). For example, the below
        snippet results in the same two task identifiers as the one above::

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

        See individual methods' API docs for details.
        """
        # Initialize
        self.tasks = Lexicon()
        self.collections = Lexicon()
        self.default = None
        self.name = None
        self._configuration = {}
        # Name if applicable
        args = list(args)
        if args and isinstance(args[0], six.string_types):
            self.name = args.pop(0)
        # Specific kwargs if applicable
        self.loaded_from = kwargs.pop('loaded_from', None)
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
            raise TypeError("No idea how to insert {0!r}!".format(type(obj)))
        return method(obj, name=name)

    def __repr__(self):
        return "<Collection {0!r}: {1}>".format(
            self.name,
            ", ".join(sorted(self.tasks.keys())),
        )

    def __eq__(self, other):
        return self.name == other.name and self.tasks == other.tasks

    @classmethod
    def from_module(self, module, name=None, config=None, loaded_from=None):
        """
        Return a new `.Collection` created from ``module``.

        Inspects ``module`` for any `.Task` instances and adds them to a new
        `.Collection`, returning it. If any explicit namespace collections
        exist (named ``ns`` or ``namespace``) a copy of that collection object
        is preferentially loaded instead.

        When the implicit/default collection is generated, it will be named
        after the module's ``__name__`` attribute, or its last dotted section
        if it's a submodule. (I.e. it should usually map to the actual ``.py``
        filename.)

        Explicitly given collections will only be given that module-derived
        name if they don't already have a valid ``.name`` attribute.

        :param str name:
            A string, which if given will override any automatically derived
            collection name (or name set on the module's root namespace, if it
            has one.)

        :param dict config:
            Used to set config options on the newly created `.Collection`
            before returning it (saving you a call to `.configure`.)

            If the imported module had a root namespace object, ``config`` is
            merged on top of it (i.e. overriding any conflicts.)

        :param str loaded_from:
            Identical to the same-named kwarg from the regular class
            constructor - should be the path where the module was
            found.
        """
        module_name = module.__name__.split('.')[-1]
        # See if the module provides a default NS to use in lieu of creating
        # our own collection.
        for candidate in ('ns', 'namespace'):
            obj = getattr(module, candidate, None)
            if obj and isinstance(obj, Collection):
                # TODO: make this into Collection.clone() or similar
                # Explicitly given name wins over root ns name which wins over
                # actual module name.
                ret = Collection(name or obj.name or module_name,
                                 loaded_from=loaded_from)
                ret.tasks = copy.deepcopy(obj.tasks)
                ret.collections = copy.deepcopy(obj.collections)
                ret.default = copy.deepcopy(obj.default)
                # Explicitly given config wins over root ns config
                obj_config = copy_dict(obj._configuration)
                if config:
                    merge_dicts(obj_config, config)
                ret._configuration = obj_config
                return ret
        # Failing that, make our own collection from the module's tasks.
        tasks = filter(
            lambda x: isinstance(x, Task),
            vars(module).values()
        )
        # Again, explicit name wins over implicit one from module path
        collection = Collection(name or module_name, loaded_from=loaded_from)
        for task in tasks:
            collection.add_task(task)
        if config:
            collection.configure(config)
        return collection

    def add_task(self, task, name=None, default=None):
        """
        Add `.Task` ``task`` to this collection.

        :param task: The `.Task` object to add to this collection.

        :param name:
            Optional string name to bind to (overrides the task's own
            self-defined ``name`` attribute and/or any Python identifier (i.e.
            ``.func_name``.)

        :param default: Whether this task should be the collection default.
        """
        if name is None:
            if task.name:
                name = task.name
            elif hasattr(task.body, 'func_name'):
                name = task.body.func_name
            elif hasattr(task.body, '__name__'):
                name = task.__name__
            else:
                raise ValueError("Could not obtain a name for this task!")
        if name in self.collections:
            raise ValueError("Name conflict: this collection has a sub-collection named {0!r} already".format(name)) # noqa
        self.tasks[name] = task
        for alias in task.aliases:
            self.tasks.alias(alias, to=name)
        if default is True or (default is None and task.is_default):
            if self.default:
                msg = "'{0}' cannot be the default because '{1}' already is!"
                raise ValueError(msg.format(name, self.default))
            self.default = name

    def add_collection(self, coll, name=None):
        """
        Add `.Collection` ``coll`` as a sub-collection of this one.

        :param coll: The `.Collection` to add.

        :param str name:
            The name to attach the collection as. Defaults to the collection's
            own internal name.
        """
        # Handle module-as-collection
        if isinstance(coll, types.ModuleType):
            coll = Collection.from_module(coll)
        # Ensure we have a name, or die trying
        name = name or coll.name
        if not name:
            raise ValueError("Non-root collections must have a name!")
        # Test for conflict
        if name in self.tasks:
            raise ValueError("Name conflict: this collection has a task named {0!r} already".format(name)) # noqa
        # Insert
        self.collections[name] = coll

    def split_path(self, path):
        """
        Obtain first collection + remainder, of a task path.

        E.g. for ``"subcollection.taskname"``, return ``("subcollection",
        "taskname")``; for ``"subcollection.nested.taskname"`` return
        ``("subcollection", "nested.taskname")``, etc.

        An empty path becomes simply ``('', '')``.
        """
        parts = path.split('.')
        coll = parts.pop(0)
        rest = '.'.join(parts)
        return coll, rest

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
        return self.task_with_config(name)[0]

    def _task_with_merged_config(self, coll, rest, ours):
        task, config = self.collections[coll].task_with_config(rest)
        return task, dict(config, **ours)

    def task_with_config(self, name):
        """
        Return task named ``name`` plus its configuration dict.

        E.g. in a deeply nested tree, this method returns the `.Task`, and a
        configuration dict created by merging that of this `.Collection` and
        any nested `Collections <.Collection>`, up through the one actually
        holding the `.Task`.

        See `~.Collection.__getitem__` for semantics of the ``name`` argument.

        :returns: Two-tuple of (`.Task`, `dict`).
        """
        # Our top level configuration
        ours = self.configuration()
        # Default task for this collection itself
        if not name:
            if self.default:
                return self[self.default], ours
            else:
                raise ValueError("This collection has no default task.")
        # Non-default tasks within subcollections -> recurse (sorta)
        if '.' in name:
            coll, rest = self.split_path(name)
            return self._task_with_merged_config(coll, rest, ours)
        # Default task for subcollections (via empty-name lookup)
        if name in self.collections:
            return self._task_with_merged_config(name, '', ours)
        # Regular task lookup
        return self.tasks[name], ours

    def __contains__(self, name):
        try:
            self[name]
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
            result.append(ParserContext(
                name=primary, aliases=aliases, args=task.get_arguments()
            ))
        return result

    def subtask_name(self, collection_name, task_name):
        return '.'.join([collection_name, task_name])

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

    def configuration(self, taskpath=None):
        """
        Obtain merged configuration values from collection & children.

        :param taskpath:
            (Optional) Task name/path, identical to that used for
            `~.Collection.__getitem__` (e.g. may be dotted for nested tasks,
            etc.) Used to decide which path to follow in the collection tree
            when merging config values.

        :returns: A `dict` containing configuration values.
        """
        if taskpath is None:
            return copy_dict(self._configuration)
        return self.task_with_config(taskpath)[1]

    def configure(self, options):
        """
        (Recursively) merge ``options`` into the current `.configuration`.

        Options configured this way will be available to all tasks. It is
        recommended to use unique keys to avoid potential clashes with other
        config options

        For example, if you were configuring a Sphinx docs build target
        directory, it's better to use a key like ``'sphinx.target'`` than
        simply ``'target'``.

        :param options: An object implementing the dictionary protocol.
        :returns: ``None``.
        """
        merge_dicts(self._configuration, options)
