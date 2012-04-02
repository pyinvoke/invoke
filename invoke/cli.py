import argparse

from .loader import Loader


def main():
    # Parse
    parser = argparse.ArgumentParser()
    # TODO: make it create a list, not a string
    parser.add_argument('--collection', '-c')
    parser.add_argument('--root', '-r')
    # TODO: Take 1+ tasks
    parser.add_argument('task')

    args = parser.parse_args()

    # Load
    collection = Loader(root=args.root).load_collection(args.collection)
    task = collection.get(args.task)

    # Invoke
    task()
