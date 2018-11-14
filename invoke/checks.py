# TODO: what should these look like exactly?
# TODO: what data is available to them? what's their signature? anything, or
# just assume it's 100% external information? (Seems unwise - what about checks
# that assert things about config?)
# TODO: built-in checks:
# - file exists and/or is modified more recently than something else (???)
# - any others, really? prob just extract from real world usage?


def exists(path):
    """
    Ensures a given file path exists

    :returns:
        a check callable which itself returns `True` if the path exists, or
        `False` otherwise.
    """
    # TODO: this doesn't really want to exist, right? users should just do:
    # @task(check=lambda: os.path.exists(path)) right???
    # TODO: does it want to be @task(requires=[...]) instead?
    pass


def newer_than(path, otherpath):
    """
    Ensures ``path`` exists and is the same age, or newer, than ``otherpath``.
    """
    # TODO: this probably wants to exist, right? or is there another easy
    # lambda containing a stdlib function?
    pass


# TODO: maybe steal some good ideas from prior art? can we even just use them
# wholesale? but then why even use invoke if we're gonna ask you to use
# bake/paver/whatever...heh
