from invoke import task

@task
def bar(ctx):
  print "hello world\n"
