.. _concepts-tasks in classes:

====================================
Using classes to make sets of tasks.
====================================

While Collections offer a powerful way of grouping common tasks together, and
creating useful namespace hierarchies, they don't solve all forms of grouping,
and they certainly don't reduce repeated code problems. Take for example, the
following case:

A company offers a SaaS solution as its product. The site and api exposed to
the world is actually composed of several smaller "micro-services", each of
which is run by uwsgi in emperor mode. There is a uwsgi task file, which
provides some common useful functions and tasks, to help manage the servics.
This looks something like this::

    from invoke import ctask as task

    # helpers
    def convert_name_to_config(ctx, servicename):
       return "{}/{}/configs/uwsgi.ini".format(ctx.get("service_dir"),
                                               servicename)

    # tasks
    @task()
    def start(ctx):
        ctx.run("sudo start uwsgi")

    # ... other service functions, stop, restart, etc

    @task
    def start_endpoint(ctx, endpoint_name):
        source_config = convert_name_to_config(ctx, endpoint_name)
        ctx.run("cp {} /etc/uwsgi/{}.ini".format(source_config, endpoint_name)

    @task
    def stop_endpoint(ctx, endpoint_name):
        # if already stopped, don't error on rm
        ctx.run("rm -f  /etc/uwsgi/{}.ini".format(endpoint_name)

    # ... other enpoint functions: reload, etc

Each service also has a task file associated with it. Service1 looks like::

    from invoke import ctask as task
    from uwsgi_tasks import ns as uwsgi

    SVC_NAME='Service1'

    @task
    def install_to_virtualenv(ctx, venv=SVCNAME):
        # ... pip stuff, other config stuff

    @task
    def start(ctx):
        uwsgi['start_endpoint'](ctx, SVC_NAME)

    @task
    def stop(ctx):
        uwsgi['stop_endpoint'](ctx, SVC_NAME)

    @task
    def configure(ctx, service1_a="default_a", service1_b="default_b):
        do_service1_specific_thing(service1_a, service1_b)

Service2 similarly looks like::

    from invoke import ctask as task
    from uwsgi_tasks import ns as uwsgi

    SVC_NAME='Service2'

    @task
    def install_to_virtualenv(ctx, venv=SVCNAME):
        # ... pip stuff, other config stuff

    @task
    def start(ctx):
        uwsgi['start_endpoint'](ctx, SVC_NAME)

    @task
    def stop(ctx):
        uwsgi['stop_endpoint'](ctx, SVC_NAME)

    @task
    def configure(ctx, service2_a="default_a"):
        do_service2_specific_thing(service2_a)

ServiceN is slightly different::

    from invoke import ctask as task
    from uwsgi_tasks import ns as uwsgi

    SVC_NAME='ServiceN'

    @task
    def install_to_virtualenv(ctx, venv=SVCNAME):
        # ... pip stuff, other config stuff

    @task
    def start(ctx):
        start_some_sidekick()
        uwsgi['start_endpoint'](ctx, SVC_NAME)

    @task
    def stop(ctx):
        uwsgi['stop_endpoint'](ctx, SVC_NAME)

    @task
    def configure(ctx, service1_a="default_a", service1_b="default_b):
        do_serviceN_specific_thing(serviceN_a, serviceN_b)


As you can see - the differences between Service1 and Service2 are confined to
``SVC_NAME`` and the ``configure()`` task. If this was a true pattern, the
repetition could be solved with a bit of collection wrangling and configuration
variable magic. However, as seen with ServiceN, sometimes the individual
functions change a bit (i.e. the ``start`` task). So the simple solution (so
far) is to have a task file for each Service, and just repeat the code around
when needed.

However there are at least 2 major problems with this:

1. When something changes in the uwsgi_tasks api, there are N service taskfiles
   that need to be changed to keep up to date.
2. When a convention changes for service operations, each file needs to be
   changed. This is complicated by the fact that necessary differences in a
   service taskfile may be hard to distinguise from missed convention updates.

A nice solution to these problems is to offer a class based set of tasks. The
class can serve as a template for common functionality, clarify when a specific
deviation is intentional, and reduce the scope of error by omission for
changes.  Such a mechanism transforms the above service structure like so:

uswgi_tasks remains unchanged.

There is a new file, service_base like this::

    from invoke import ctask as task, callback_task, TaskTemplate
    from uwsgi_tasks import ns as uwsgi

    class ServiceBase(TaskTemplate):
        def __init__(self, service_name, config_callback):
            self.service_name = service_name
            self.config_callback = config_callback

        @task
        def install_to_virtualenv(self, ctx, venv=SVCNAME):
            # ... pip stuff, other config stuff

        @task
        def start(self, ctx):
            uwsgi['start_endpoint'](ctx, self.service_name)

        @task
        def stop(self, ctx):
            uwsgi['stop_endpoint'](ctx, self.service_name)

        @callback_task(callback_func = "config_callback")
        def configure(ctx, *args, **kw):
            self.config_callback(ctx, *args, **kw)

Service1 becomes::

    from service_base import ServiceBase

    def configure(ctx, service1_a="default_a", service1_b="default_b):
        do_service1_specific_thing(service1_a, service1_b)

    ns = ServiceBase("Service1", configure).to_collection()

Service2 becomes::

    from service_base import ServiceBase

    def configure(ctx, service2_a="default_a"):
        do_service2_specific_thing(service2_a)

    ns = ServiceBase("Service2", configure).to_collection()

and ServiceN becomes::

    from invoke import ctask as task
    from service_base import ServiceBase

    SVC_NAME='ServiceN'

    class ServiceN(ServiceBase):

        @task
        def start(self, ctx):
            start_some_sidekick()
            super(ServiceN, self).start(ctx)

        @task
        def configure(ctx, service1_a="default_a", service1_b="default_b):
            do_serviceN_specific_thing(serviceN_a, serviceN_b)

    ns = ServiceN('ServiceN', None).to_collection()


This is (relatively) painless to create, and provides simplification!

Other similar use cases:

* Docker containers
* systemd or upstart services
* test system wrappers
* build system wrappers

Design Thoughts
---------------

Firstly, this is just a design spike - there are many diferent ways to acheive
the concepts here, with various mechanism... there are a lot of pros and cons
about the details, but conceptually, they provide very similar results!

In the above example, there are a few poorly defined notions that need to be
expanded upon:

* ``TaskTemplate`` - this is a (currently) fictional base class that provides a
  method called ``to_collection``. The operation of it is to turn an object
  into a ``Collection()``. In order to do this operation, there is a variety of
  book-keeping that needs to be done about methods in the class, the difference
  between instances and classes, (and therefore unbound vs bound methods) and
  many other such details.

* ``callback_task`` - another fictional notion, but the operation here is based
  on the assumption that there are one or a few tasks that are expected to
  differ across instances of a ``TaskTemplate`` subclass. As such, rather than
  requiring a new class for each instance, there can be a way to register a
  simple callback which allows that variance. An important operation of the
  ``callback_task`` is that the argspec reported is that of the callback rather
  than the wrapping method - so collections are properly build, argument
  handling is properly dealt with, and so on.

* ``@task`` works on method definitions - this is just a shorthand on my part
  to keep away from the bikeshed. In reality, this may need to be a separate
  decorator, or the normal task decorators will need severe refactoring.


No matter what the final details work out to be, there are a few challenges
that need to be addressed.

* Function vs Bound Method vs Unbound Method vs Callable object - each of these
  has subtly different semantics that need to be unified. Invoke currently
  handles (in this branch) a distinction between Function, Method and Callable
  object. The distinction betweeen bound and unbound methods is a matter of
  checking that the function has its ``im_self`` attribute set or not. However,
  the handling of Unbound methods needs to be thought out.

* Requiring collections to be formed from instances rather than classes. This
  isn't strictly required, but it dives into meta-magic rather quickly without
  doing so. It can be done, but it's scary and ugly and while metaclasses are
  for frameworks, going this route touches an absurd amount of the rest of
  ``invoke``. So the real question here is how can this be structured so that
  it is (a) easily explainable to the 'new to invoke' crowd, and (b) is easy to
  generate an error that explains the exact problem

* How to work this in so it doesn't feel bolted on to the rest of invoke as an
  after thought. Rather it should be pretty seamless to the rest of operation.

* are there potential use cases that don't follow the pattern laid out above?
  (some people, for instance, really like mixins, how does that change stuff?)

* what the heck do we call this.. seriously I like none of the idea's I've come
  up with :) (however something around the Template thought is favorable in my
  head right now)
