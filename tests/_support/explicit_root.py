"""
EXPLICIT LYRICS
"""

from invoke import task, Collection


@task(aliases=["other_top"])
def top_level(c):
    pass


@task(aliases=["other_sub"], default=True)
def sub_task(c):
    pass


sub = Collection("sub_level", sub_task)
ns = Collection(top_level, sub)
