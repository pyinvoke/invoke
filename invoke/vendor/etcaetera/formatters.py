from collections import namedtuple


def uppercased(s):
    return s.upper()


def lowercased(s):
    return s.lower()


def environ(s):
    return s.strip().upper().replace(' ', '_')
