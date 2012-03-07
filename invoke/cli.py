import argparse
import os
import sys


def go(args):
    parent = os.path.dirname(os.path.abspath(args.file))
    sys.path.insert(0, parent)
    module = os.path.splitext(os.path.basename(args.file))[0]
    imported = __import__(module)
    options = vars(imported)
    if args.task in options:
        return options[args.task]()
    



def main():
    parser = argparse.ArgumentParser()
    # TODO: make it create a list, not a string
    # TODO: default to ['tasks']
    parser.add_argument('--collection', '-c')
    # TODO: Take 1+ tasks
    parser.add_argument('task')

    args = parser.parse_args()
    return go(args)
