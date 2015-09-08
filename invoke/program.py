class Program(object):
    """
    Manages top-level CLI invocation, typically via setup.py entrypoints.

    Designed for distributing Invoke task collections as standalone programs,
    but also used internally to implement the ``invoke`` program itself.

    .. seealso::
        :ref:`reusing-as-a-binary` for a tutorial/walkthrough of this
        functionality.
    """
    def __init__(self, version, namespace=None, name=None, binary=None):
        """
        Create a new, parameterized `.Program` instance.

        :param str version: The program's version, e.g. ``"0.1.0"``.

        :param namespace:
            A `.Collection` to use as this program's subcommands.
            
            If ``None`` (the default), the program will behave like ``invoke``,
            seeking a nearby task namespace with a `.Loader` and exposing
            arguments such as :option:`--list` and :option:`--collection` for
            inspecting or selecting specific namespaces.
            
            If given a `.Collection` object, will use it as if it had been
            handed to :option:`--collection`. Will also update the parser to
            remove references to tasks and task-related options, and display
            the subcommands in ``--help`` output. The result will be a program
            that has a static set of subcommands.

        :param str name:
            The program's name, as displayed in ``--version`` output.

            If ``None`` (default), is a capitalized version of the first word
            in the ``argv`` handed to `.run`. For example, when invoked from a
            binstub installed as ``foobar``, it will default to ``Foobar``.

        :param str binary:
            The binary name as displayed in ``--help`` output.

            If ``None`` (default), uses the first word in ``argv`` verbatim (as
            with ``name`` above, except not capitalized).

            Giving this explicitly may be useful when you install your program
            under multiple names, such as Invoke itself does - it installs as
            both ``inv`` and ``invoke``, and sets ``name="inv[oke]"`` so its
            ``--help`` output implies both names.
        """
        self.version = version
        self.namespace = namespace

    def run(self, argv=None):
        """
        Execute main CLI logic, based on ``argv``.

        :param argv:
            The arguments to execute against.
            
            **If None** (the default), uses `sys.argv` itself.

            **If a list**, uses that in place of `sys.argv`.

            **If a string**, performs a `str.split` and then executes with the
            result.
        """
