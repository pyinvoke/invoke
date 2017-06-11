from invoke.vendor.six.moves.queue import Queue

from invoke.exceptions import ExceptionWrapper
from invoke.util import ExceptionHandlingThread as EHThread

from spec import Spec, ok_, eq_


# TODO: rename
class ExceptionHandlingThread_(Spec):
    class via_target:
        def setup(self):
            def worker(q):
                q.put(7)
            self.worker = worker

        def base_case(self):
            queue = Queue()
            t = EHThread(target=self.worker, args=[queue])
            t.start()
            t.join()
            eq_(queue.get(block=False), 7)
            ok_(queue.empty())

        def catches_exceptions(self):
            # Induce exception by submitting a bad queue obj
            t = EHThread(target=self.worker, args=[None])
            t.start()
            t.join()
            wrapper = t.exception()
            ok_(isinstance(wrapper, ExceptionWrapper))
            eq_(wrapper.kwargs, {'args': [None], 'target': self.worker})
            eq_(wrapper.type, AttributeError)
            ok_(isinstance(wrapper.value, AttributeError))

        def exhibits_is_dead_flag(self):
            t = EHThread(target=self.worker, args=[None])
            t.start()
            t.join()
            ok_(t.is_dead)
            t = EHThread(target=self.worker, args=[Queue()])
            t.start()
            t.join()
            ok_(not t.is_dead)

    class via_subclassing:
        def setup(self):
            class MyThread(EHThread):
                def __init__(self, *args, **kwargs):
                    self.queue = kwargs.pop('queue')
                    super(MyThread, self).__init__(*args, **kwargs)

                def _run(self):
                    self.queue.put(7)
            self.klass = MyThread

        def base_case(self):
            queue = Queue()
            t = self.klass(queue=queue)
            t.start()
            t.join()
            eq_(queue.get(block=False), 7)
            ok_(queue.empty())

        def catches_exceptions(self):
            # Induce exception by submitting a bad queue obj
            t = self.klass(queue=None)
            t.start()
            t.join()
            wrapper = t.exception()
            ok_(isinstance(wrapper, ExceptionWrapper))
            eq_(wrapper.kwargs, {})
            eq_(wrapper.type, AttributeError)
            ok_(isinstance(wrapper.value, AttributeError))

        def exhibits_is_dead_flag(self):
            t = self.klass(queue=None)
            t.start()
            t.join()
            ok_(t.is_dead)
            t = self.klass(queue=Queue())
            t.start()
            t.join()
            ok_(not t.is_dead)
