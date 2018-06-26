from invoke.vendor.six.moves.queue import Queue

from invoke.util import ExceptionWrapper, ExceptionHandlingThread as EHThread


# TODO: rename
class ExceptionHandlingThread_:
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
            assert queue.get(block=False) == 7
            assert queue.empty()

        def catches_exceptions(self):
            # Induce exception by submitting a bad queue obj
            t = EHThread(target=self.worker, args=[None])
            t.start()
            t.join()
            wrapper = t.exception()
            assert isinstance(wrapper, ExceptionWrapper)
            assert wrapper.kwargs == {"args": [None], "target": self.worker}
            assert wrapper.type == AttributeError
            assert isinstance(wrapper.value, AttributeError)

        def exhibits_is_dead_flag(self):
            t = EHThread(target=self.worker, args=[None])
            t.start()
            t.join()
            assert t.is_dead
            t = EHThread(target=self.worker, args=[Queue()])
            t.start()
            t.join()
            assert not t.is_dead

    class via_subclassing:
        def setup(self):
            class MyThread(EHThread):
                def __init__(self, *args, **kwargs):
                    self.queue = kwargs.pop("queue")
                    super(MyThread, self).__init__(*args, **kwargs)

                def _run(self):
                    self.queue.put(7)

            self.klass = MyThread

        def base_case(self):
            queue = Queue()
            t = self.klass(queue=queue)
            t.start()
            t.join()
            assert queue.get(block=False) == 7
            assert queue.empty()

        def catches_exceptions(self):
            # Induce exception by submitting a bad queue obj
            t = self.klass(queue=None)
            t.start()
            t.join()
            wrapper = t.exception()
            assert isinstance(wrapper, ExceptionWrapper)
            assert wrapper.kwargs == {}
            assert wrapper.type == AttributeError
            assert isinstance(wrapper.value, AttributeError)

        def exhibits_is_dead_flag(self):
            t = self.klass(queue=None)
            t.start()
            t.join()
            assert t.is_dead
            t = self.klass(queue=Queue())
            t.start()
            t.join()
            assert not t.is_dead
