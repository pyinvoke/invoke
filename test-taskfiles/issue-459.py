from invoke import context


if __name__ == '__main__':
  c = context.Context()
  with c.cd('/tmp/'):
    c.run('pwd')
    c.sudo('echo $PWD $USER', user="postgres")
