import argparse

from .loader import Loader


def main():
    parser = argparse.ArgumentParser()
    # TODO: make it create a list, not a string
    # TODO: default to ['tasks']
    parser.add_argument('--collection', '-c')
    parser.add_argument('--root', '-r')
    # TODO: Take 1+ tasks
    parser.add_argument('task')

    args = parser.parse_args()

    collection = Loader(root=args.root).load_collection(args.collection)
    collection.get(args.task)()
